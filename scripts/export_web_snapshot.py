"""Publish only the pinned, verified Phase 1 public comparison as read-only assets."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil

from brca_review.ingestion.tsv import sha256

EXPECTED = 'db13a977ca45c52a405778bf78eaf187b0e595d893298660187ea20776b3bfb6'


def export(source: Path, destination: Path, manifest_path: Path) -> None:
    if sha256(source) != EXPECTED:
        raise ValueError('Input must be the verified Phase 1 CSV; reproduce it using the pinned manifest.')
    manifest = json.loads(manifest_path.read_text())
    rows = list(csv.DictReader(source.open(encoding='utf-8', newline='')))
    for row in rows:
        for side in ('previous', 'current'):
            release = manifest['releases'][0 if side == 'previous' else 1]
            for key in ('release_date', 'sha256'):
                if row[f'{side}_{key}'] != release[key]:
                    raise ValueError('Manifest and comparison provenance disagree')
            for field in ('classification', 'review_status', 'genes', 'source_lines'):
                row[f'{side}_{field}'] = json.loads(row[f'{side}_{field}'])
    counts = dict(sorted(Counter(row['status'] for row in rows).items()))
    data = dict(schema_version=1, gene='BRCA1', comparison_sha256=EXPECTED,
                releases=manifest['releases'], counts=counts, rows=rows)
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'comparison.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    (destination/'releases.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (destination/'health').write_text(json.dumps(dict(status='ok', mode='read-only-snapshot',
                                                   comparison_sha256=EXPECTED))+'\n')
    shutil.copyfile(source, destination/'comparison.csv')
    print(f'Exported {len(rows)} public variant records to {destination}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('outputs/brca1.csv'))
    parser.add_argument('--output', type=Path, default=Path('frontend/public/api'))
    parser.add_argument('--manifest', type=Path, default=Path('docs/releases.json'))
    args = parser.parse_args()
    export(args.input, args.output, args.manifest)
