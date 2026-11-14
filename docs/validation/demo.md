# Reproducible technical demo — Phase 4 preparation

This walkthrough uses actual published records. It is a demonstration, not a
human pilot, an independent clinical review, or proof that this workflow improves
care. The current source-reference status is pending independent approval.

## Run from a clean checkout

Requires Python3.11+ for file-only work, or Python3.12 with the tested lock file
for the web stack; Node24/pnpm11.19 for local frontend builds; Docker Engine and
Compose for PostgreSQL/application containers. Original raw archives total
approximately1.2GB compressed. Allow several GB of free disk for derived files,
images and a database. Source hashes and schemas are pinned in the public manifests.

```sh
# 1. Download/verify and reproduce the exact historical comparisons.
PYTHONPATH=src python3 scripts/download_releases.py
PYTHONPATH=src python3 scripts/download_releases.py --manifest docs/submission-releases.json
PYTHONPATH=src python3 -m brca_review.cli --manifest docs/releases.json --output outputs/brca1.csv
PYTHONPATH=src python3 -m brca_review.cli --genes BRCA1 BRCA2 --manifest docs/releases.json --output outputs/brca1-brca2.csv
PYTHONPATH=src python3 -m brca_review.submission_cli --output outputs/submissions-final.jsonl
# 2. Independently inspect source fields for the fixed benchmark.
python3 scripts/build_validation_benchmark.py
# 3. Prepare legacy assets, own credentials and PostgreSQL service.
PYTHONPATH=src python3 scripts/export_web_snapshot.py
test -f .env || cp .env.example .env
# Edit .env to set your own unique password before starting containers.
docker compose up -d --wait db
# 4. Build/migrate/import explicitly, then start the read-only app.
docker compose -f compose.frontend.yaml build
docker compose -f compose.frontend.yaml --profile tools run --rm migrate
docker compose -f compose.frontend.yaml --profile tools run --rm importer
docker compose -f compose.frontend.yaml up -d --wait api frontend
# 5. Check the real DB-backed app against independently inspected evidence.
PYTHONPATH=src python3 scripts/verify_validation_app.py --base-url http://127.0.0.1:8091
```

Use another Compose project/ports for a parallel local check; never reset a
populated database, delete its volume or change production routing for a demo.
Infrastructure/public deployment remains owned by VPS Codex. Full commands and
network/credential details are in [frontend operations](../frontend.md) and
[storage operations](../storage.md). Standard-library tests remain independent
of PostgreSQL and Node; optional integration tests use an isolated test database.

## Walkthrough in the UI

Open the local frontend, select **both genes** and the actual January/February
2025 pair. Paste [watchlist.txt](watchlist.txt) into the public-ID field and apply.
Check the filters: 16 aggregate cases comprise four changed, eight unchanged,
two newly observed and two unavailable. No missing or unresolved real case is
claimed. The UI's pagination/export must include the full selected set even
when the default changed-only filter displays fewer rows.

1. **37422 (BRCA1):** open the aggregate detail. January is Uncertain significance;
   February is Conflicting classifications of pathogenicity. Inspect source
   filenames, dates, lines, hashes and review status. This is not a diagnosis.
2. **91425 (BRCA2):** select unchanged aggregates. Its aggregate remains
   Conflicting classifications of pathogenicity. Open **SCV000184021** in the
   separate verified-submission section: Ambry Genetics .8→.9, Uncertain
   significance→Likely benign, mapped condition C0027672. Show both evaluation
   dates separately from the publication interval.
3. **141093 (BRCA1):** independently inspected second SCV change with the same
   stable-aggregate pattern. Do not generalize from two examples to all submissions.
4. **37574:** SCV000296299 remains Pathogenic, but its condition changes to not
   provided; inspect the context flag rather than claiming a classification change.
5. **38235:** SCV005437124.1 is newly observed in the newer source. It was absent
   from the complete earlier scan. New here means newly observed between files,
   not the exact date a laboratory submitted or first evaluated the assertion.
6. **3393452 / 3481928:** new aggregate IDs; 3393452 lists only Fanconi anemia and is an explicit clinical-scope challenge, not a verified hereditary-cancer example. Old source rows are absent, not an
   inferred old VUS. **54119 / 51037:** unavailable classifications are separate
   from unchanged records.

Filter by condition C0027672 and submitter Ambry to inspect both changed SCVs.
Clear a filter or use a nonexistent submitter to show the explicit empty/limited
coverage message. No matching verified SCV is not complete surveillance evidence.
Current ClinVar links navigate to today's page; dated archive rows prove history.

## What the kit demonstrates

A reproducible path from exact public sources to raw old/new values and source
provenance, plus correct separation of aggregate and SCV levels and operational
states. It does not demonstrate clinical benefit, complete condition/SCV coverage,
independent adjudication, or improved review time/accuracy. To test those
hypotheses, first complete the [protocol gates](protocol.md).

Generate an empty scoring report to confirm that no observations are invented:

```sh
PYTHONPATH=src python3 scripts/score_validation.py \
  --responses docs/validation/responses-template.csv \
  --sessions docs/validation/sessions-template.csv \
  --output outputs/validation/no-participant-results.json
```

Expected: `no_participant_data`, zero human participants, empty result groups,
null timing/usefulness conclusions. Do not publish synthetic scorer test outputs
as observed reviewer results. Real observation files stay under ignored local
`outputs/validation/` until a separately reviewed, privacy-appropriate release.
