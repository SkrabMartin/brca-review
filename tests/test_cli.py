"""Exercise the actual offline CLI with tiny synthetic dated releases."""
import csv
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from brca_review.ingestion.tsv import sha256


class CliTests(unittest.TestCase):
    def test_reproducible_cli_and_rejected_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            headers = ['VariationID', 'GeneSymbol', 'ClinicalSignificance', 'ReviewStatus']
            releases = []
            for day, value in [('2025-01-02', 'Uncertain significance'), ('2025-02-06', 'Benign')]:
                path = root / f'{day}.gz'
                with gzip.open(path, 'wt') as f:
                    f.write('\t'.join(headers)+'\n')
                    f.write(f'1\tBRCA1\t{value}\tcriteria provided\n')
                releases.append(dict(filename=path.name, headers=headers, sha256=sha256(path),
                                     release_date=day, url=f'https://example.org/{path.name}'))
            manifest = root / 'manifest.json'
            meta = dict(format='clinvar-variant-summary-tsv-v1', releases=releases)
            manifest.write_text(json.dumps(meta))
            base = [sys.executable, '-m', 'brca_review.cli', '--manifest', str(manifest),
                    '--data-dir', str(root), '--output']
            for name in ['one.csv', 'two.csv']:
                result = subprocess.run(base+[str(root/name)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root/'one.csv').read_bytes(), (root/'two.csv').read_bytes())
            with (root/'one.csv').open() as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row['status'], 'changed')
            self.assertEqual(row['previous_sha256'], releases[0]['sha256'])
            self.assertEqual(json.loads(row['current_source_lines']), [2])
            releases.reverse()
            manifest.write_text(json.dumps(meta))
            result = subprocess.run(base+[str(root/'bad.csv')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('chronological', result.stderr)
            self.assertFalse((root/'bad.csv').exists())
