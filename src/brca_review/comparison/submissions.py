"""Compare SCV identities without silently equating different assertion contexts."""
from brca_review.comparison.aggregate import UNAVAILABLE

CONTEXT = ('variation_id', 'submitted_condition', 'reported_condition', 'submitter_name', 'classification_type')
METADATA = ('review_status', 'last_evaluated', 'collection_method', 'origin_counts', 'submitted_gene')


def compare_submissions(previous: dict, current: dict):
    for scv in sorted(previous.keys() | current.keys()):
        old, new = previous.get(scv, []), current.get(scv, [])
        # Keep somatic records during extraction so type transitions are not called disappearance.
        if all(r['classification_type'] == 'somatic' for r in old + new):
            continue
        flags = []
        if len(old) > 1 or len(new) > 1:
            status = 'unresolved'
        elif not old:
            status = 'newly_observed'
        elif not new:
            status = 'missing'
        else:
            before, after = old[0], new[0]
            flags = [f'{key}_changed' for key in (*CONTEXT, *METADATA, 'scv_version', 'classification')
                     if before[key] != after[key]]
            if any(before[key] != after[key] for key in CONTEXT):
                status = 'context_changed'
            elif (before['classification'].lower() in UNAVAILABLE or
                  after['classification'].lower() in UNAVAILABLE):
                status = 'unavailable'
            elif before['classification'] != after['classification']:
                status = 'classification_changed'
            else:
                status = 'unchanged'
        yield dict(scv_base=scv, status=status, flags=flags, previous=old, current=new)
