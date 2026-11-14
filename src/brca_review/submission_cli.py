"""Database-free SCV comparison for BRCA1/BRCA2; emits deterministic JSON Lines."""
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path

from brca_review.ingestion.tsv import extract
from brca_review.ingestion.submissions import extract_submissions
from brca_review.comparison.aggregate import compare
from brca_review.comparison.submissions import compare_submissions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant-manifest', type=Path, default=Path('docs/releases.json'))
    parser.add_argument('--submission-manifest', type=Path, default=Path('docs/submission-releases.json'))
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    parser.add_argument('--genes', nargs='+', choices=['BRCA1', 'BRCA2'], default=['BRCA1', 'BRCA2'])
    parser.add_argument('--variants', nargs='+', help='Optional explicit public-ID subset')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        vm = json.loads(args.variant_manifest.read_text())
        sm = json.loads(args.submission_manifest.read_text())
        if vm['format'] != 'clinvar-variant-summary-tsv-v1' or sm['format'] != 'clinvar-submission-summary-tsv-v1':
            raise ValueError('Unsupported manifest format')
        if len(vm['releases']) != 2 or len(sm['releases']) != 2:
            raise ValueError('Exactly two releases are required')
        dates = [r['release_date'] for r in vm['releases']]
        if dates != [r['release_date'] for r in sm['releases']] or date.fromisoformat(dates[0]) >= date.fromisoformat(dates[1]):
            raise ValueError('Variant/submission release dates must match and be chronological')
        inputs = [args.data_dir/r['filename'] for r in vm['releases']+sm['releases']]
        if args.output.resolve() in {p.resolve() for p in inputs+[args.variant_manifest, args.submission_manifest]}:
            raise ValueError('Output cannot overwrite inputs')
        snapshots = [extract(args.data_dir/r['filename'], r, frozenset(args.genes)) for r in vm['releases']]
        ids = snapshots[0].keys() | snapshots[1].keys()
        if args.variants:
            if not set(args.variants) <= ids:
                raise ValueError('Requested variant not in selected gene snapshots')
            ids = set(args.variants)
        aggregates = {i: status for i, status, *_ in compare(*snapshots)}
        submissions = [extract_submissions(args.data_dir/r['filename'], r, set(ids)) for r in sm['releases']]
        if not any(submissions):
            raise ValueError('No submissions in selected scope')
        args.output.parent.mkdir(exist_ok=True, parents=True)
        counts = Counter()
        with args.output.open('w', encoding='utf-8', newline='') as stream:
            for event in compare_submissions(*submissions):
                involved = {r['variation_id'] for r in event['previous']+event['current']}
                event.update(observed_between=dates,
                             aggregate_status={i:aggregates[i] for i in sorted(involved, key=int)},
                             aggregate_classifications={i:{side:sorted(snapshots[n][i].values) if i in snapshots[n] else []
                                 for n,side in enumerate(('previous','current'))} for i in sorted(involved,key=int)},
                             scope=dict(genes=sorted(set(args.genes)), variants=sorted(ids, key=int) if args.variants else 'all_gene_overlaps',
                                        condition_filter='none; clinical scope not reviewed'))
                stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True)+'\n')
                counts[event['status']] += 1
        print(json.dumps(dict(sorted(counts.items())), sort_keys=True))
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f'Submission comparison failed: {error}\n')


if __name__ == '__main__':
    main()
