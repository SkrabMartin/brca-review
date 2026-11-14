"""Database-free end-to-end SCV CLI test with labeled synthetic source files."""
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from brca_review.ingestion.tsv import sha256
from brca_review.ingestion.submissions import FIELDS


class SubmissionCliTests(unittest.TestCase):
    def test_provenance_context_and_invalid_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            vr=[];sr=[]
            for i,day in enumerate(['2025-01-02','2025-02-06']):
                vp=root/f'v{i}.gz';sp=root/f's{i}.gz'
                vh=['VariationID','GeneSymbol','ClinicalSignificance','ReviewStatus']
                with gzip.open(vp,'wt') as f:
                    f.write('\t'.join(vh)+'\n1\tBRCA2\tConflicting classifications\tcriteria provided\n')
                raw={key:'-' for key in FIELDS.values()}
                raw.update({'#VariationID':'1','ClinicalSignificance':['Uncertain significance','Benign'][i],
                            'SCV':f'SCV000000001.{i+1}','Submitter':'Example Lab',
                            'SubmittedPhenotypeInfo':'MedGen:C123','ReportedPhenotypeInfo':'C123:Example',
                            'DateLastEvaluated':'Jan 01, 2020'})
                sh=list(FIELDS.values())
                with gzip.open(sp,'wt') as f:
                    f.write('##Synthetic\n'+'\t'.join(sh)+'\n'+'\t'.join(raw[h] for h in sh)+'\n')
                for records,path,headers in [(vr,vp,vh),(sr,sp,sh)]:
                    records.append(dict(filename=path.name,headers=headers,sha256=sha256(path),
                                        release_date=day,url='https://example.org/'+path.name))
            vm=root/'variants.json';sm=root/'submissions.json';out=root/'events.jsonl'
            vm.write_text(json.dumps(dict(format='clinvar-variant-summary-tsv-v1',releases=vr)))
            meta=dict(format='clinvar-submission-summary-tsv-v1',releases=sr)
            sm.write_text(json.dumps(meta))
            cmd=[sys.executable,'-m','brca_review.submission_cli','--variant-manifest',str(vm),
                 '--submission-manifest',str(sm),'--data-dir',str(root),'--output',str(out)]
            run=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            event=json.loads(out.read_text())
            self.assertEqual(event['status'],'classification_changed')
            self.assertEqual(event['aggregate_status'],{'1':'unchanged'})
            self.assertEqual(event['previous'][0]['last_evaluated'],'Jan 01, 2020')
            self.assertEqual(event['observed_between'],['2025-01-02','2025-02-06'])
            first=out.read_bytes()
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertEqual(out.read_bytes(),first)
            self.assertNotEqual(subprocess.run(cmd+['--variants','99'],capture_output=True).returncode,0)
            sr[1]['release_date']='2025-03-06';sm.write_text(json.dumps(meta))
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
