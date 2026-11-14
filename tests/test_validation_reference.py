"""Integrity of the published provisional kit; never treats it as a human result."""
import csv
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
KIT=ROOT/'docs/validation'


class ValidationReferenceTests(unittest.TestCase):
    def test_fixed_public_case_balance_and_task_contract(self):
        data=json.loads((KIT/'benchmark.json').read_text())
        self.assertEqual(len(data['cases']),16)
        self.assertEqual(len({c['variation_id'] for c in data['cases']}),16)
        for gene in ['BRCA1','BRCA2']:self.assertEqual(sum(c['gene']==gene for c in data['cases']),8)
        self.assertEqual(len(data['scored_tasks']),21)
        self.assertEqual(len({t['task_id'] for t in data['scored_tasks']}),21)
        self.assertEqual(sum(t['status'] in data['positive_statuses'] for t in data['scored_tasks']),10)
        for case in data['cases']:
            self.assertTrue(case['variation_id'].isdigit())
            for index,side in enumerate(['previous','current']):
                source=data['sources']['variant'][index]
                for row in case['aggregate'][side]:
                    self.assertEqual(row['source_sha256'],source['sha256'])
                    self.assertEqual(row['release_date'],data['publication_dates'][index])
                    self.assertGreater(row['source_line'],1)
        with (KIT/'tasks.csv').open(newline='') as f:tasks=list(csv.DictReader(f))
        self.assertEqual({t['task_id'] for t in tasks},{t['task_id'] for t in data['scored_tasks']})
        self.assertNotIn('status',tasks[0]) # Participant tasks do not contain answer labels.
        with (KIT/'reference.csv').open(newline='') as f:reference=list(csv.DictReader(f))
        self.assertEqual({r['task_id'] for r in reference},{t['task_id'] for t in tasks})
        self.assertEqual(set((KIT/'watchlist.txt').read_text().split()),{c['variation_id'] for c in data['cases']})

    def test_pilot_pending_no_observations_in_templates(self):
        data=json.loads((KIT/'benchmark.json').read_text())
        self.assertEqual(data['verification']['human_pilot'],'not_run')
        self.assertEqual(data['verification']['participants'],0)
        self.assertEqual(data['verification']['independent_reviewer'],'pending')
        self.assertFalse(any(data['baseline_eligibility'].values()))
        for name in ['responses-template.csv','sessions-template.csv','review-log-template.csv','assignments-template.csv']:
            with (KIT/name).open(newline='') as f:
                reader=csv.DictReader(f);self.assertTrue(reader.fieldnames);self.assertEqual(list(reader),[])
        result=json.loads((KIT/'results-status.json').read_text())
        self.assertEqual(result['status'],'no_participant_data')
        self.assertEqual(result['human_participant_count'],0)
        self.assertEqual(result['results'],[])
        self.assertIsNone(result['usefulness_conclusion'])
        self.assertIsNone(result['median_net_seconds_saved'])
        with (KIT/'scope-review.csv').open(newline='') as f:scope=list(csv.DictReader(f))
        self.assertEqual(len(scope),16)
        self.assertTrue(all(r['scope_status']=='pending_clinical_review' and not r['inclusion_decision'] for r in scope))
        challenge=next(r for r in scope if r['case_id']=='C06')
        self.assertIn('Fanconi',challenge['source_condition_context'])
