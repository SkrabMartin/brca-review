# Validation preparation — provisional reference, no human pilot yet

This kit prepares Phase 4; it does **not** establish clinical validity or reviewer
benefit. The account holder confirmed that no independent geneticist/curator is
yet available. Human participants: **0**. Independent clinical/reference approval:
**pending**. No measured reviewer times, accuracy differences, or clinical
outcomes are reported.

## Public artifacts

- [Benchmark](benchmark.json): 16 public variants, eight per gene, with exact
  selected source fields and provenance. Agent-inspected, not clinician-approved.
- [Reference sheet](reference.csv): 16 aggregate tasks plus five SCV tasks;
  investigator material, not a participant answer sheet.
- [Task sheet](tasks.csv): identifiers and release interval without reference
  answers; use this for participants after the study gates pass.
- [Watchlist](watchlist.txt): public IDs to paste into the existing app.
- [Scope-review sheet](scope-review.csv): pending inclusion decisions; C06 is an explicit scope challenge, not an established hereditary-cancer case.
- [Protocol](protocol.md): task/endpoint definitions, fair baselines, order and
  timing rules, scoring, limitations, and completion gates.
- [Demo walkthrough](demo.md): technical reproduction and source inspection.
- [Baseline access check](baseline-access.json): automated access probe, with
  direct-web historical usability explicitly unverified.
- [Responses](responses-template.csv), [sessions](sessions-template.csv),
  [assignments](assignments-template.csv), and [independent review](review-log-template.csv):
  **header-only templates**, not observations or recruited participants.
- [Current results status](results-status.json): explicitly no participant data.

Actual responses, assignments and reviewer notes belong in ignored local
`outputs/validation/`, using pseudonymous codes and public variants only. Never
include patient records, names or sensitive clinical notes in public artifacts.
The study protocol/reference are reproducible public scientific documentation;
internal phase reports and project/agent instructions remain local.

## Preparation and technical verification

From the project root, with the pinned raw releases already downloaded:

```sh
python3 scripts/build_validation_benchmark.py
# Optional new access probe; output is local, not a clinical availability approval:
python3 scripts/probe_validation_baseline.py
PYTHONPATH=src python3 scripts/verify_validation_app.py --base-url https://brca.skrabana.com
PYTHONPATH=src python3 scripts/score_validation.py \
  --responses docs/validation/responses-template.csv \
  --sessions docs/validation/sessions-template.csv \
  --output outputs/validation/empty-results.json
PYTHONPATH=src python3 -S -m unittest discover -s tests -p test_validation.py -v
```

The builder independently scans all four complete source files (not the app
extractor/API), verifies source hashes/headers, checks explicit absence of new
records, and cross-checks the five SCVs against the earlier inspected evidence.
It exports selected public summary fields only, omitting free-text rationale.
Rebuilding preserves fixed case order and deterministic content. It overwrites
only reference/template files, not actual observations in `outputs/validation/`.
Source inspection by software and agent is not independent clinical adjudication.

The app verifier compares its read-only HTTP responses with the provisional
reference and checks explicit submission coverage. It does not update the DB,
UI, sources, proxy, DNS or deployment. Empty templates yield no human
participants, no outcome metrics, no timing estimate and no usefulness conclusion.
Scorer tests use explicitly synthetic fixtures; their perfect scores are not
study results.

## Pending gates

Obtain independent source and clinical-scope review, verify historical baseline
access for every timed task, freeze a reviewed reference/protocol, recruit
reviewers, then collect and analyze genuine observations. Phase 4 remains open
until those steps are completed and reported. A negative usefulness result is
valid; no result is preferable to invented participation or favorable metrics.
