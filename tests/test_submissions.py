"""Synthetic assertions only; historical verification is documented separately."""
import copy
import gzip
from pathlib import Path
import tempfile
import unittest

from brca_review.ingestion.submissions import FIELDS, extract_submissions
from brca_review.ingestion.tsv import sha256
from brca_review.comparison.submissions import compare_submissions


def assertion(**changes):
    row = dict(variation_id='1', classification='Uncertain significance',
        last_evaluated='Jan 01, 2020', submitted_condition='MedGen:C123',
        reported_condition='C123:Example condition', review_status='criteria provided',
        submitter_name='Example laboratory', scv='SCV000001.1', scv_base='SCV000001',
        scv_version=1, classification_type='germline', collection_method='clinical testing',
        origin_counts='germline:na', submitted_gene='BRCA2', source_lines=[20])
    row.update(changes)
    return row


class SubmissionTests(unittest.TestCase):
    def event(self, old, new):
        return next(compare_submissions({'SCV000001': old} if old else {},
                                        {'SCV000001': new} if new else {}))

    def test_changed_new_missing_unchanged_and_dates(self):
        old = assertion()
        new = assertion(classification='Likely benign', scv_version=2, scv='SCV000001.2')
        event = self.event([old], [new])
        self.assertEqual(event['status'], 'classification_changed')
        self.assertEqual(event['previous'][0]['last_evaluated'], 'Jan 01, 2020')
        self.assertEqual(self.event([], [old])['status'], 'newly_observed')
        self.assertEqual(self.event([old], [])['status'], 'missing')
        self.assertEqual(self.event([old], [copy.deepcopy(old)])['status'], 'unchanged')

    def test_context_and_versions_not_silently_collapsed(self):
        old = assertion()
        for field, value in [('submitted_condition', 'other'), ('reported_condition', 'C234:Other'),
                             ('submitter_name', 'Other lab'), ('variation_id', '2'),
                             ('classification_type', 'somatic')]:
            event = self.event([old], [assertion(**{field:value})])
            self.assertEqual(event['status'], 'context_changed')
            self.assertIn(field+'_changed', event['flags'])
        event = self.event([old], [assertion(scv='SCV000001.2', scv_version=2,
                                            last_evaluated='Jan 01, 2021')])
        self.assertEqual(event['status'], 'unchanged')
        self.assertIn('last_evaluated_changed', event['flags'])
        self.assertEqual(self.event([old, assertion(classification='Benign')], [old])['status'], 'unresolved')
        self.assertEqual(self.event([assertion(classification='-')], [old])['status'], 'unavailable')
        self.assertEqual(list(compare_submissions({'S':[assertion(classification_type='somatic')]}, {})), [])

    def test_source_extraction_duplicate_and_missing_gene(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'fixture.gz'
            headers = list(FIELDS.values())
            row = assertion(submitted_gene='-')
            row.update(somatic_clinical_impact='-', oncogenicity='-')
            values = [str(row[k]) for k in FIELDS]
            with gzip.open(path, 'wt') as f:
                f.write('##Synthetic file\n'+'\t'.join(headers)+'\n')
                f.write('\t'.join(values)+'\n')
                f.write('\t'.join(values)+'\n')
                other = list(values);other[0] = '99';f.write('\t'.join(other)+'\n')
            meta = dict(sha256=sha256(path), headers=headers, url='https://example.org/data',release_date='2025-01-02')
            records = extract_submissions(path, meta, {'1'})
            item = records['SCV000001'][0]
            self.assertEqual(item['source_lines'], [3,4])
            self.assertEqual(item['scv_version'], 1)
            self.assertEqual(item['condition_medgen_ids'], ['C123'])
            self.assertIsNone(item['rcv_accessions'])
            self.assertIsNone(item['submitter_id'])
            self.assertEqual(item['release_date'], '2025-01-02')
            with self.assertRaises(ValueError):
                extract_submissions(path, dict(meta, sha256='bad'), {'1'})
