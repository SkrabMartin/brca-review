"""Pure aggregate comparison; no database, network, or UI dependency."""

from brca_review.ingestion.tsv import Record

UNAVAILABLE = {'', '-', 'na', 'not provided', 'no classification provided'}


def compare(previous: dict[str, Record], current: dict[str, Record]):
    for identifier in sorted(previous.keys() | current.keys(), key=int):
        before, after = previous.get(identifier), current.get(identifier)
        if (before and before.unresolved) or (after and after.unresolved):
            status = 'unresolved'
        elif before is None:
            status = 'newly_observed'
        elif after is None:
            status = 'missing'
        elif (next(iter(before.values)).lower() in UNAVAILABLE or
              next(iter(after.values)).lower() in UNAVAILABLE):
            status = 'unavailable'
        elif before.values != after.values:
            status = 'changed'
        else:
            status = 'unchanged'
        yield identifier, status, before, after
