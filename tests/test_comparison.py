"""Synthetic fixtures, not historical ClinVar findings."""
import gzip
from pathlib import Path
import tempfile
import unittest

from brca_review.comparison.aggregate import compare
from brca_review.ingestion.tsv import Record, extract, sha256


def record(value, review='criteria provided'):
    return Record({value}, {review}, {'BRCA1'}, [2])


class ComparisonTests(unittest.TestCase):
    def test_states_and_numeric_order(self):
        old = {'2': record('VUS'), '10': record('Benign'), '3': record('-'),
               '4': record('Benign'), '6': record('VUS')}
        new = {'2': record('Likely benign'), '10': record('Benign'), '3': record('VUS'),
               '5': record('Benign'), '6': Record({'VUS', 'Benign'}, {'criteria provided'})}
        self.assertEqual([(i, s) for i, s, *_ in compare(old, new)],
                         [('2', 'changed'), ('3', 'unavailable'), ('4', 'missing'),
                          ('5', 'newly_observed'), ('6', 'unresolved'), ('10', 'unchanged')])

    def test_duplicate_assemblies_gene_tokens_and_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.gz'
            headers = ['VariationID', 'GeneSymbol', 'ClinicalSignificance', 'ReviewStatus']
            with gzip.open(path, 'wt') as f:
                f.write('\t'.join(headers) + '\n')
                f.write('1\tBRCA1\tBenign\tcriteria provided\n' * 2)
                f.write('2\tBRCA10\tBenign\tcriteria provided\n')
                f.write('4\tBRCA2\tPathogenic\tcriteria provided\n')
                f.write('3\tBRCA1,OTHER\tVUS\tcriteria provided\n')
                f.write('3\tBRCA1,OTHER\tBenign\tcriteria provided\n')
            meta = dict(sha256=sha256(path), headers=headers)
            rows = extract(path, meta)
            self.assertEqual(set(rows), {'1', '3'})
            self.assertEqual(set(extract(path, meta, frozenset({'BRCA2'}))), {'4'})
            self.assertEqual(set(extract(path, meta, frozenset({'BRCA1','BRCA2'}))), {'1','3','4'})
            self.assertEqual(rows['1'].lines, [2, 3])
            self.assertFalse(rows['1'].unresolved)
            self.assertTrue(rows['3'].unresolved)
            with self.assertRaises(ValueError):
                extract(path, dict(meta, sha256='bad'))
            with self.assertRaises(ValueError):
                extract(path, dict(meta, headers=['wrong']))

    def test_review_only_change_is_not_classification_change(self):
        self.assertEqual(next(compare({'1': record('Benign')},
                                      {'1': record('Benign', 'expert panel')}))[1], 'unchanged')


if __name__ == '__main__':
    unittest.main()
