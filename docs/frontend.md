# Phase 3 React frontend and application containers

The React/TypeScript/Vite frontend retains the existing table-oriented design.
It now calls a real, read-only Python API backed by PostgreSQL. It supports
loaded release-pair selection, BRCA1/BRCA2 filtering, public-ID watchlists,
classification search/status filters, pagination, CSV export, aggregate source
details, and a **five-SCV verified subset** with condition/submitter filters.
Missing SCV examples do not imply unchanged submissions. No patient records or
user review decisions are accepted/stored.

## Build inputs

Follow [persistence setup](storage.md) to prepare PostgreSQL, migrations, and
import the pinned Phase 1/2 artifacts. A clean checkout must first recreate the
ignored outputs using the root README comparison commands. Retain the original
Phase 1 snapshot export for legacy routes:

```sh
PYTHONPATH=src python3 scripts/export_web_snapshot.py
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm test
corepack pnpm build
corepack pnpm dev
```

Node 24, React/TypeScript/Vite, and pnpm 11.19.0 follow BKP's conventions. Vite
proxies `/api/v1` to `http://127.0.0.1:8093` during development. The browser
always calls relative URLs; no private hostname or credential is compiled into
the JavaScript. The legacy exporter accepts only the verified Phase 1 CSV.

## Docker application stack

After preparing input artifacts:

```sh
# Own PostgreSQL service/volume/network; does not touch BKP.
docker compose up -d --wait db
# Both backend and frontend production images:
docker compose -f compose.frontend.yaml build
# Explicit one-shot schema/data operations:
docker compose -f compose.frontend.yaml --profile tools run --rm migrate
docker compose -f compose.frontend.yaml --profile tools run --rm importer
docker compose -f compose.frontend.yaml up -d --wait api frontend
curl -fsS http://127.0.0.1:8091/api/v1/health
```

`compose.frontend.yaml` uses the external project-specific database network
`brca-review_default`, created by `compose.yaml`. It shares only BRCA Review's
own DB, never BKP resources. Environment variables are explicitly passed to the
backend/tools only. The frontend receives no DB credentials. Migration and
import are opt-in tools, not public API operations or frontend build effects.
The importer mounts ignored `outputs/` read-only. API runtime has no source
artifact mount. Backend Docker context is default-deny and includes only code,
migrations, packaging and reviewed public JSON manifests/examples.

Frontend container: unprivileged Nginx, internal 8080, loopback host
`BRCA_FRONTEND_PORT=8091`. API container: internal 8000, loopback host
`BRCA_API_PORT=8093`. Database health/import readiness is checked through
`/api/v1/health`; frontend startup waits for API health, and its own container health check also calls `/api/v1/health`. The legacy frontend
`/api/health` checks only the static snapshot, not PostgreSQL.

For an isolated local preview beside the existing public deployment, choose a
separate Compose project and host ports, e.g. `-p brca-review-mvp-test` and
`BRCA_FRONTEND_PORT=8092 BRCA_API_PORT=8093`. Point it to an explicitly created
BRCA Review test database if needed. Never bind API/DB ports publicly.

## Routing contract for the VPS owner

The external proxy can continue to send **all paths unchanged to the frontend
host port 8091**. Inside Nginx, `/api/v1/*` forwards unchanged to `api:8000`;
SPA assets/routes are handled locally. The old `/api/comparison.json`, CSV,
manifest and `/api/health` remain pinned Phase 1 legacy resources. Unknown API
paths return 404 rather than SPA HTML. Static resources are not a database
fallback if the new API fails. Request access logs are disabled in the app
containers so public watchlist query strings need not be retained.

DNS, HTTPS, external proxy and public rollout remain the VPS workspace owner's
responsibility. If the external proxy is in a separate container, its localhost
is not the host: choose the appropriate shared application network or host-network
upstream. Database port 5433 must never be routed into the public site.

## Verification and limits

Run React tests/build and the optional PostgreSQL integration suite. Browser
checks should exercise an unchanged aggregate with a changed SCV (91425), both
genes, unknown/invalid/duplicate/versioned IDs, status and condition/submitter
filters, source detail, CSV and empty/error states. Test mobile widths 320, 390,
and 768 by comparing document scrollWidth to clientWidth, including open details.

Only January/February 2025 are currently imported. Evaluation dates are separate
from release intervals. Clinical scope and reviewer usefulness remain unvalidated;
Phase 4 will evaluate these with qualified reviewers. The standard-library
comparison CLIs continue to work without the web, Node, or database packages.
