"""File-only BRCA1/BRCA2 comparison: python -m brca_review.cli --help."""

import argparse
from collections import Counter
import csv
from datetime import date
import json
from pathlib import Path

from brca_review.comparison.aggregate import compare
from brca_review.ingestion.tsv import extract


def main() -> None:
    parser = argparse.ArgumentParser(description='Compare BRCA1/BRCA2 aggregate germline classifications.')
    parser.add_argument('--genes', nargs='+', choices=['BRCA1', 'BRCA2'], default=['BRCA1'])
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        if manifest['format'] != 'clinvar-variant-summary-tsv-v1':
            raise ValueError('Unsupported manifest format')
        before, after = manifest['releases']
        if date.fromisoformat(before['release_date']) >= date.fromisoformat(after['release_date']):
            raise ValueError('Release dates must be chronological')
        paths = [args.data_dir / r['filename'] for r in (before, after)]
        if args.output.resolve() in {p.resolve() for p in paths} | {args.manifest.resolve()}:
            raise ValueError('Output must not overwrite an input')
        snapshots = [extract(p, r, frozenset(args.genes)) for p, r in zip(paths, (before, after))]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        counts = Counter()
        fields = ['variation_id', 'status', 'clinvar_url']
        suffixes = ['release_date', 'classification', 'review_status', 'genes',
                    'source_lines', 'source_url', 'sha256']
        fields += [f'{side}_{key}' for side in ('previous', 'current') for key in suffixes]
        with args.output.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            for identifier, status, old, new in compare(*snapshots):
                row = dict(variation_id=identifier, status=status,
                           clinvar_url=f'https://www.ncbi.nlm.nih.gov/clinvar/variation/{identifier}/')
                for side, record, release in [('previous', old, before), ('current', new, after)]:
                    row[f'{side}_release_date'] = release['release_date']
                    row[f'{side}_source_url'] = release['url']
                    row[f'{side}_sha256'] = release['sha256']
                    # JSON arrays preserve multiple conflicting raw values without ambiguity.
                    row[f'{side}_classification'] = json.dumps(sorted(record.values)) if record else '[]'
                    row[f'{side}_review_status'] = json.dumps(sorted(record.review_statuses)) if record else '[]'
                    row[f'{side}_genes'] = json.dumps(sorted(record.genes)) if record else '[]'
                    row[f'{side}_source_lines'] = json.dumps(record.lines) if record else '[]'
                writer.writerow(row)
                counts[status] += 1
        print(json.dumps(dict(sorted(counts.items())), sort_keys=True))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f'Comparison failed: {error}\n')


if __name__ == '__main__':
    main()
