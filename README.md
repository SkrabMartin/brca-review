# BRCA Review

BRCA Review is a proposed bioinformatics application for clinical geneticists
and variant curators reviewing changes in public ClinVar records for germline
BRCA1 and BRCA2 variants associated with hereditary cancer predisposition.
It will compare dated releases and show previous/current values, conditions,
submitters where applicable, and traceable sources. Interpretation stays with
the reviewer.

**Status:** Phase 0 repository foundation. No ingestion, comparison, database,
or web interface is implemented. The first milestone is a reproducible BRCA1
aggregate germline classification comparison before a web UI is built.

ClinVar already offers [aggregate classification alerts](https://www.ncbi.nlm.nih.gov/clinvar/docs/alerts/);
the added value of batch review and submission-level history is a hypothesis
to test. Source data will be attributed to ClinVar.

## Architecture

```text
Dated public ClinVar releases
  -> ingestion: explicit source manifest and snapshot extraction
  -> comparison: deterministic old/new events by stable identifiers
  -> storage: SQLite snapshots, relationships, provenance, and events
  -> presentation: Streamlit batch review and variant details
```

Comparison will operate independently of SQLite and Streamlit so that it can
run from a command line and be tested on small fixtures. Phase 0 provides only
package boundaries; later components are planned below.

| Phase | Components and locations |
| --- | --- |
| 0: foundation | This README, packaging configuration, ignore rules, package skeleton |
| 1: BRCA1 comparison | `src/brca_review/ingestion/`, `src/brca_review/comparison/`, future `src/brca_review/cli.py`, `tests/`, and `docs/` release manifest/verification log |
| 2: BRCA2, conditions, submissions | Extend ingestion/comparison; future `src/brca_review/models.py`; matching fixtures in `tests/` and scope documentation in `docs/` |
| 3: web MVP | Future `src/brca_review/storage/` for SQLite and root `app.py` for Streamlit; public-ID watchlist and detail views |
| 4: validation/demo | Hand-checked public examples and evaluation in `docs/`, regression fixtures in `tests/`, reproducible run instructions here |

Preserve stable ClinVar Variation IDs and VCV accession versions, raw values,
both release dates, exact source filenames/URLs, and checksums. Later phases
will retain RCV variant–condition relationships and individual SCV accessions,
versions, condition identifiers, and submitter identifiers rather than flattening
them into a single classification. Last-evaluated dates will remain distinct
from the interval in which a change is observed. Missing records are explicit
states, not inferred reclassifications. Field mappings and release availability
must be verified against the actual dated files.

See [data documentation](docs/README.md) and [test planning](tests/README.md).
Downloaded releases belong in ignored `data/`; generated databases and outputs
belong in ignored `outputs/`. Neither directory is needed for Phase 0.

## Development

Requires Python 3.11 or newer. To install the package skeleton locally:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -c "import brca_review"
```

There is no runnable comparison or demo yet. Runtime dependencies and commands
will be added with their implementation phases. Agent instructions, credentials,
and internal planning stay local. Stage public paths explicitly and inspect both
the index and every commit to be pushed; stop publication if internal material
appears. Planning documents remain local and are excluded regardless of filename capitalization.

## Next implementation task

Inspect official ClinVar archives and record two accessible dated releases in
a source manifest. Check actual headers/schema versions and determine whether
TSV supports the BRCA1 aggregate germline comparison; otherwise select compatible
archived VCV XML. Do this before implementing a parser or UI.
