# BRCA Review

BRCA Review helps clinical geneticists and variant curators review published
changes in public ClinVar records for germline **BRCA1 and BRCA2** variants.
It compares dated releases and preserves previous/current values, condition
and submitter context where supported, and traceable source evidence.
Interpretation stays with the reviewer.

**Status:** Phase 3 web MVP implemented: PostgreSQL persistence, Alembic
migrations, a read-only API, and the React frontend. Both genes' aggregate
snapshots are available; submission coverage is deliberately limited to **five
source-verified SCV examples**. Clinical disease scope and reviewer usefulness
are not validated. The separate standard-library comparison CLIs remain usable
without PostgreSQL, web dependencies, or Node.

ClinVar already offers [aggregate classification alerts](https://www.ncbi.nlm.nih.gov/clinvar/docs/alerts/).
The added value of batch review and submission context is a hypothesis to test.
All biological record data are attributed to NCBI ClinVar. No patient records or
user review decisions are accepted/stored by this MVP.

## Architecture

```text
Dated public ClinVar TSV releases
  -> ingestion: exact source hashes, headers, field mappings and row provenance
  -> comparison: pure Python aggregate and condition-preserving SCV events
  -> optional PostgreSQL storage: immutable snapshots, contexts and events
  -> read-only Python HTTP API under /api/v1
  -> React / TypeScript / Vite: batch public-ID review and source details
```

| Component | Location |
| --- | --- |
| Dated sources and verification | `docs/`, `scripts/download_releases.py` |
| File-only extraction/comparison | `src/brca_review/ingestion/`, `src/brca_review/comparison/` |
| File-only CLIs | `src/brca_review/cli.py`, `src/brca_review/submission_cli.py` |
| PostgreSQL/SQLAlchemy models and import | `src/brca_review/storage/` |
| Alembic schema history | `alembic.ini`, `migrations/` |
| Read-only HTTP adapter | `src/brca_review/web/` |
| Public web frontend | `frontend/` |
| Synthetic and optional PostgreSQL tests | `tests/` |

The database stack follows BKP: **PostgreSQL 17, SQLAlchemy 2 with Psycopg 3
(`postgresql+psycopg://`), Alembic, and Docker Compose**. BRCA Review uses its
own database, configuration, credentials, network and volume. Its public
frontend follows BKP's Node 24 / pnpm / React / TypeScript / Vite conventions.
FastAPI provides the now-needed database read API; parsing and comparison never
import it. Streamlit remains an optional future analytical view.

## File-only reproduction

Requires Python 3.11+ and the standard library only. From the project root:

```sh
PYTHONPATH=src python3 scripts/download_releases.py
PYTHONPATH=src python3 scripts/download_releases.py --manifest docs/submission-releases.json
PYTHONPATH=src python3 -m brca_review.cli --manifest docs/releases.json --output outputs/brca1.csv
PYTHONPATH=src python3 -m brca_review.cli --genes BRCA1 BRCA2 --manifest docs/releases.json --output outputs/brca1-brca2.csv
PYTHONPATH=src python3 -m brca_review.submission_cli --output outputs/submissions-final.jsonl
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Downloads total approximately 1.2 GB compressed; allow additional disk/memory
for outputs (the full SCV JSONL is about 284 MB). Sources are the actual archived
publication dates **2025-01-02 → 2025-02-06**. Every downloaded input is checked
against its compressed-byte SHA-256. Both file CLIs refuse incompatible headers
and mismatched/nonchronological dates. Outputs sort deterministically and retain
raw classification spelling, source URLs/hashes, dates, and line numbers.

- Original BRCA1 comparison: 46 changed, 12,591 unchanged, 104 newly observed,
  2,229 unavailable. No missing/unresolved records in this pair.
- BRCA1+BRCA2 aggregate union: 34,356 IDs; 113 changed, 31,633 unchanged,
  352 newly observed, 2,258 unavailable.
- Full SCV discovery: 111 same-context classification changes, 92 context
  changes, 1,405 newly observed, 4,654 unavailable and 108,472 unchanged.
  This discovery output is **not** all represented as verified web examples.

Re-running the same command to a second output and comparing with `cmp` verifies
byte reproducibility. The original BRCA1 CLI output remains unchanged after the
BRCA2/storage extensions. Synthetic tests are distinct from historical evidence.

See [variant source mapping](docs/release-manifest.md), [variant manifest](docs/releases.json),
[historical aggregate verification](docs/verification.md),
[SCV semantics and commands](docs/submissions.md),
[submission manifest](docs/submission-releases.json), and
[historical SCV verification](docs/submission-verification.md).

## Local PostgreSQL and migrations

Copy [the placeholder environment](.env.example) to ignored `.env` and set a
unique password; never reuse BKP credentials. PostgreSQL binds by default to
`127.0.0.1:5433`, with database/role `brca_review`, project network
`brca-review_default`, and volume `brca-review_postgres_data`.

```sh
test -f .env || cp .env.example .env
# Edit .env before starting: replace the password placeholder.
docker compose up -d --wait db
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-web.lock
.venv/bin/python -m pip install --no-deps -e .
set -a
. ./.env
set +a
.venv/bin/python scripts/check_database.py
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/python -m brca_review.storage.importer
```

Prepare the file-only outputs first. The importer verifies pinned artifact
hashes and independently checked SCV example fields; it imports all aggregate
rows and only five verified SCV events/nine assertion snapshots. Re-importing
the same immutable pair is a no-op. API startup never creates schema or imports
data. See [storage and API documentation](docs/storage.md) for schema and tests.

Changing initialization credentials in `.env` does not change an existing
PostgreSQL volume's role/password. Stop with `docker compose stop db` or
`docker compose down` to retain data. Do not remove the volume or run schema
downgrades on data you need to keep. Downgrade tests use disposable databases.

## Web MVP

The UI retains its table-oriented design and adds actual loaded release-pair
selection, both genes, public Variation ID/unversioned VCV watchlists (max 200),
explicit invalid/duplicate/absent-ID feedback, classification/status filtering,
pagination, filtered CSV export, and source detail. A separate verified-SCV
section filters by condition, submitter, and event type and distinguishes
release dates from assertion evaluation dates.

```sh
# Generate the original legacy snapshot assets once:
PYTHONPATH=src python3 scripts/export_web_snapshot.py
# Build both production images after preparing .env and the DB:
docker compose -f compose.frontend.yaml build
docker compose -f compose.frontend.yaml --profile tools run --rm migrate
docker compose -f compose.frontend.yaml --profile tools run --rm importer
docker compose -f compose.frontend.yaml up -d --wait api frontend
curl -fsS http://127.0.0.1:8091/api/v1/health
```

Frontend: loopback **8091**, Nginx container **8080**. API: loopback **8093**,
container **8000**. The external proxy can route all paths unchanged to the
frontend; Nginx forwards relative `/api/v1/*` to the API internally. The old
`/api/health` and snapshot downloads remain Phase 1 legacy resources; use
`/api/v1/health` for PostgreSQL/import readiness. No CORS or private backend URL
is required in browser code. PostgreSQL/API ports must not be published directly.

For frontend development, `cd frontend`, run `corepack pnpm install --frozen-lockfile`,
`corepack pnpm test`, `corepack pnpm build`, then `corepack pnpm dev`; start the
API on loopback 8093 as described in [frontend deployment documentation](docs/frontend.md).
Do not replace an existing public service while verifying a new local increment:
use another Compose project and `BRCA_FRONTEND_PORT=8092` for an isolated preview.

Application code is managed in `~/projects/brca-review` on `skrablinux`.
Target public URL: `https://brca.skrabana.com`. Proxy, DNS, HTTPS and public
rollout are owned by VPS Codex in `~/projects/VPS`.

## Scope and next work

Gene membership is not a clinically approved hereditary-cancer condition filter.
Raw condition context is preserved without inferred ontology equivalence.
Stable submitter IDs, VCV versions and SCV–RCV links absent from TSV stay null.
No matching verified SCV is not evidence that all other submissions are unchanged.
Current ClinVar links are navigation aids; historical evidence is the exact
archived source. A string difference is not a diagnosis or an automatic clinical
reclassification.

Next is reviewer validation: a small hand-checked benchmark and a fair comparison
of time/accuracy with direct ClinVar review. Clinical scope and usefulness remain
open until that work is performed. No claim of clinical benefit is made.

Internal planning, phase reports and agent instructions stay local regardless
of capitalization. Stage public paths explicitly and inspect the index and all
outgoing commits before any push. Raw data, generated output and credentials
remain ignored; public documentation never links internal planning documents.

## Phase 4 validation preparation

A [provisional validation kit](docs/validation/README.md) now contains 16 public
variants (eight per gene), 21 review tasks, independently re-extracted raw-source
evidence, a reference sheet, a watchlist, header-only observation/review templates,
a reproducible demo, and scoring tools. The reference was checked by the
implementation agent; **independent clinical review is pending**.

Human participants: **0**. There are no measured reviewer times or usefulness
results. Both timing-comparison gates remain closed. The direct ClinVar website
probe encountered a browser-verification page; historical task accessibility
requires a qualified reviewer check. An archive-assisted control is separately
named and must not be presented as direct web review. One source-condition scope
challenge (Fanconi anemia) is explicitly flagged for inclusion review.

```sh
python3 scripts/build_validation_benchmark.py
PYTHONPATH=src python3 scripts/verify_validation_app.py --base-url http://127.0.0.1:8091
PYTHONPATH=src python3 scripts/score_validation.py --responses docs/validation/responses-template.csv --sessions docs/validation/sessions-template.csv --output outputs/validation/results.json
```

With empty templates, scoring returns `no_participant_data`, zero human
participants and null timing/usefulness conclusions. Actual observations stay
in ignored local `outputs/validation/`. See [pilot protocol](docs/validation/protocol.md)
and [demo instructions](docs/validation/demo.md). Technical preparation is ready;
Phase 4 remains open until independent review and a genuine reviewer pilot.
