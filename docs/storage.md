# Phase 3 persistence and read-only API

## What is stored

PostgreSQL 17 is accessed with SQLAlchemy 2 and Psycopg 3
(`postgresql+psycopg://`). Schema creation happens only through Alembic; API
startup does not run `create_all` or automatically import data. The optional
`web` dependencies are separate from both standard-library file-only CLIs.
`requirements-web.lock` pins the tested Python runtime/test environment;
install it before the local package for reproducible application builds.

| Table | Purpose |
| --- | --- |
| `source_releases` | Four dated variant/submission sources, exact URLs, filenames, hashes, sizes, headers and retrieval dates |
| `variants` | Stable positive Variation IDs and annotated gene membership |
| `aggregate_snapshots` | One variant/source snapshot; raw classification/review arrays, genes and source lines |
| `condition_contexts` | Exact submitted + mapped condition strings and explicitly supplied MedGen references |
| `submission_snapshots` | Versioned SCV, variant/source relationships, condition context, submitter name, raw evaluation date, nullable unsupported identity/link fields, and original selected payload |
| `comparisons` | Supported release quartet, input artifact hashes and explicit coverage |
| `aggregate_changes` | Variant-level status for each loaded pair |
| `submission_changes` | Verified SCV event, old/new snapshot links, flags and original event evidence |

Condition hashes identify exact textual contexts, not clinical equivalence.
Submitter names are source context, not a substitute for stable submitter IDs.
SCV–RCV links, VCV versions and stable submitter IDs remain null where TSV lacks
them. The current curated importer rejects ambiguity instead of discarding
alternatives. No patient records, server watchlist table, review decisions, or
clinical reclassification rules are introduced.

## Prepare input artifacts

Run the Phase 1/2 download/comparison commands first. Then the importer expects:

- `outputs/brca1-brca2.csv`: 34,356 variant rows, both genes.
- `outputs/submissions-final.jsonl`: the full deterministic Phase 2 output.

[Artifact hashes](comparison-artifacts.json) pin these exact public inputs. The
importer verifies both hashes before opening a write transaction, and checks
selected SCV fields/status against [independent source examples](submission-examples.json).
It imports all aggregate rows but **only five verified SCV events**, comprising
nine assertion snapshots. Full Phase 2 discovery output is not automatically
represented as a fully verified public SCV dataset.

The original BRCA1 file CLI output stays unchanged. Neither file-only comparison
requires PostgreSQL, SQLAlchemy, Alembic, FastAPI, Node, or Streamlit.

## Migration and import

From the project root, after creating your own ignored `.env`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-web.lock
.venv/bin/python -m pip install --no-deps -e .
docker compose up -d --wait db
set -a
. ./.env
set +a
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/python -m brca_review.storage.importer
```

The importer uses one transaction plus a PostgreSQL advisory lock. Re-importing
the same immutable pair returns `already_imported`, without duplicated rows;
differing input hashes are refused. A failed transaction rolls back. Imports run
outside the HTTP/UI process. Do not run schema downgrades on a database whose
data must be retained. Upgrade/downgrade/upgrade was exercised only on a newly
created disposable test database, before importing its fixtures.

## API

Run locally after migrations/import:

```sh
.venv/bin/uvicorn brca_review.web.app:app --host 127.0.0.1 --port 8093 --no-access-log
```

The UI uses same-origin `/api/v1`; its Vite dev proxy targets loopback 8093.
Production Nginx forwards that prefix unchanged to `api:8000`. API queries run
in PostgreSQL read-only transactions. No write endpoints, CORS cross-origin
configuration, public import operation, or credentials in frontend variables
are provided. Operational migration/import commands use the project's own local
DB configuration; credentials are neither shared with BKP nor returned by HTTP.

| Endpoint | Contract |
| --- | --- |
| `GET /api/v1/health` | PostgreSQL connectivity, schema/query readiness, nonempty imported comparisons; 503 if not ready |
| `GET /api/v1/comparisons` | Actually loaded pairs and coverage; no fabricated dates |
| `GET /api/v1/comparison` | Selected pair/gene/watchlist, raw aggregate rows, counts, provenance and ID-validation feedback |
| `GET /api/v1/comparison.csv` | CSV for the selected pair/gene/watchlist, including all status types |
| `GET /api/v1/submissions` | Only verified SCV subset, optional gene/IDs/status/condition/submitter filters, explicit coverage |
| `GET /api/v1/variants/{id}` | One aggregate plus its verified SCV events and dated provenance |

Query parameters: `comparison_id=2025-01-02_2025-02-06`, optional
`gene=BRCA1` or `BRCA2` (omission selects both), and `ids` separated by commas,
semicolons or whitespace. Limit: 200 public identifiers / 8,000 characters.
Numeric IDs and unversioned `VCV` plus nine digits are canonicalized. Versioned
VCVs are explicitly unsupported because the TSV does not verify their versions.
Duplicates are reported and collapsed. Invalid-only input yields zero records,
not the entire database. Gene-filtered, outside-scope and absent IDs get explicit
feedback; the API cannot tell whether an unimported public variant belongs to
another gene. No live ClinVar lookups are inferred.

The fixed demo corpus permits returning all matching aggregate rows for client
filtering/pagination (maximum 34,356). This is not an unbounded live ClinVar API.
Condition and submitter filters operate on either side of verified events.
No verified SCV match must not be interpreted as all submissions unchanged.

## Tests

The normal standard-library suite skips optional storage tests when dependencies
are absent. Integration tests additionally require `BRCA_TEST_DATABASE` to match
the configured database, with a name starting `brca_review_test_`. Create and
migrate/import an isolated database first; never point these tests at the main
application database. With its configuration exported:

```sh
export BRCA_TEST_DATABASE="$BRCA_POSTGRES_DB"
.venv/bin/python -m unittest discover -s tests -v
```

Checks include migrations/model consistency, FK/check/unique constraints in
PostgreSQL, immutable import/idempotency, rejection of bad checksums, both gene
counts, ID handling, verified SCV/source/evaluation context, filters, unavailable
pairs, HTTP 404/405 and read-only transactions. The React suite verifies the same
user-facing states with explicitly synthetic fixtures. A reviewer usefulness
study remains Phase 4; these checks do not establish clinical validity.
