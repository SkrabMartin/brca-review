"""Explicitly synthetic observations test scoring; they are not reviewer results."""
import unittest
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from brca_review.validation import score


def benchmark():
    return dict(benchmark_id='SYNTHETIC_TEST_ONLY',positive_statuses=['changed','classification_changed','newly_observed','context_changed','missing'],
        verification={'independent_reviewer':'pending'},baseline_eligibility={'clinvar_web':False,'clinvar_archive':False},
        scored_tasks=[dict(task_id='C01-A',level='aggregate',variation_id='1',scv_base='',status='changed',
            previous_classification='["Uncertain significance"]',current_classification='["Benign"]'),
          dict(task_id='C02-A',level='aggregate',variation_id='2',scv_base='',status='unchanged',
            previous_classification='["Benign"]',current_classification='["Benign"]'),
          dict(task_id='C03-S',level='submission',variation_id='3',scv_base='SCV000000001',status='classification_changed',
            previous_condition='C123:Example',current_condition='C123:Example',
            previous_submitter='Example laboratory',current_submitter='Example laboratory')])


def responses(method='app'):
    return [dict(t,participant_id='SYNTHETIC_01',record_kind='synthetic',method=method,completion='complete',
                 elapsed_seconds='',excluded_seconds='') for t in benchmark()['scored_tasks']]


class ValidationScoringTests(unittest.TestCase):
    def test_no_participants_produces_no_conclusion_or_invented_metrics(self):
        result=score(benchmark(),[])
        self.assertEqual(result['status'],'no_participant_data')
        self.assertEqual(result['human_participant_count'],0)
        self.assertEqual(result['results'],[])
        self.assertIsNone(result['median_net_seconds_saved'])
        self.assertIsNone(result['usefulness_conclusion'])

    def test_perfect_synthetic_is_not_a_human_result(self):
        result=score(benchmark(),responses());r=result['results'][0]
        self.assertEqual((r['true_positive'],r['false_positive'],r['false_negative']),(2,0,0))
        self.assertEqual(r['precision'],1);self.assertEqual(r['recall'],1)
        self.assertEqual(r['status_accuracy'],1)
        self.assertEqual(result['human_participant_count'],0)
        self.assertEqual(result['synthetic_participant_count'],1)
        self.assertIsNone(result['usefulness_conclusion'])

    def test_wrong_status_wrong_identity_and_missing_task_are_not_hidden(self):
        rows=responses()[:2];rows[0]['status']='newly_observed';rows[1]['status']='changed'
        r=score(benchmark(),rows)['results'][0]
        self.assertEqual((r['true_positive'],r['false_positive'],r['false_negative']),(0,2,2))
        self.assertEqual(r['missing_responses'],1)
        self.assertEqual(r['status_accuracy'],0)
        rows=responses();rows[2]['scv_base']='SCV000000999'
        r=score(benchmark(),rows)['results'][0]
        self.assertEqual((r['true_positive'],r['false_positive'],r['false_negative']),(1,1,1))

    def test_condition_ids_and_context_attribution_scored_separately(self):
        rows=responses();rows[2]['previous_condition']='C123';rows[2]['current_submitter']='Other laboratory'
        r=score(benchmark(),rows)['results'][0]
        self.assertEqual(r['true_positive'],2)
        self.assertEqual(r['field_accuracy']['previous_condition']['correct'],1)
        self.assertEqual(r['field_accuracy']['current_submitter']['correct'],0)

    def test_invalid_duplicate_unknown_and_silent_timing_exclusions_refused(self):
        for bad in [responses()+[responses()[0]], [dict(responses()[0],task_id='UNKNOWN')],
                    [dict(responses()[0],record_kind='')], [dict(responses()[0],status='made_up')],
                    [dict(responses()[0],elapsed_seconds='nan')]]:
            with self.assertRaises(ValueError):score(benchmark(),bad)
        sessions=[dict(participant_id='SYNTHETIC_01',method='app',sequence='app_first',batch_elapsed_seconds='20',excluded_seconds='5',source_access_verified='yes')]
        with self.assertRaises(ValueError):score(benchmark(),responses(),sessions)

    def test_cli_empty_templates_malformed_csv_and_input_preservation(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);ref=path/'reference.json';answers=path/'responses.csv';out=path/'result.json'
            ref.write_text(json.dumps(benchmark()))
            answers.write_text('participant_id,record_kind,method,task_id,completion\n')
            cmd=[sys.executable,str(root/'scripts/score_validation.py'),'--benchmark',str(ref),'--responses',str(answers),'--output',str(out)]
            run=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(out.read_text())['status'],'no_participant_data')
            out.unlink();answers.write_text('participant_id,method\nBROKEN_ROW\n')
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertFalse(out.exists())
            before=ref.read_bytes()
            self.assertNotEqual(subprocess.run(cmd[:-1]+[str(ref)],capture_output=True).returncode,0)
            self.assertEqual(ref.read_bytes(),before)

    def test_excluded_task_time_is_documented_and_reported(self):
        rows=responses();rows[0].update(elapsed_seconds='20',excluded_seconds='5',exclusion_reason='Documented interruption')
        task=score(benchmark(),rows)['results'][0]['tasks'][0]
        self.assertEqual(task['elapsed_seconds'],20)
        self.assertEqual(task['excluded_seconds'],5)
        self.assertEqual(task['net_elapsed_seconds'],15)
        rows[0]['exclusion_reason']=''
        with self.assertRaises(ValueError):score(benchmark(),rows)

    def test_timing_needs_review_access_complete_sessions_and_one_baseline(self):
        rows=responses()+responses('clinvar_web')
        sessions=[dict(participant_id='SYNTHETIC_01',method=method,sequence='app_first',batch_elapsed_seconds=str(seconds),excluded_seconds='0',source_access_verified='yes')
                  for method,seconds in [('app',20),('clinvar_web',30)]]
        result=score(benchmark(),rows,sessions)
        self.assertFalse(result['paired'][0]['timing_eligible'])
        approved=benchmark();approved['verification']['independent_reviewer']='approved';approved['baseline_eligibility']['clinvar_web']=True
        result=score(approved,rows,sessions)
        self.assertEqual(result['paired'][0]['net_seconds_saved'],10)
        self.assertIsNone(result['median_net_seconds_saved']) # Synthetic excluded from human summary.
        rows[-1].update(completion='not_assessable',status='')
        result=score(approved,rows,sessions)
        self.assertFalse(result['paired'][0]['timing_eligible'])
        self.assertEqual(result['results'][1]['not_assessable'],1)


if __name__=='__main__':unittest.main()
