# Phase 2: condition-preserving submission comparison

## Sources and scope

The January and February 2025 `submission_summary` TSV archives contain
versioned SCV accessions, submitted and mapped condition text, submitter names,
germline classifications, review status, and last-evaluated dates. Both were
retrieved in full. [The source manifest](submission-releases.json) pins exact
URLs, publication/retrieval dates, compressed SHA-256 hashes, sizes, complete
headers, and the publisher's embedded column descriptions. These locally
computed hashes identify exact inputs, not publisher signatures.

January has 15 columns; February adds `ContributesToAggregateClassification`.
The contribution flag is not used because it is absent in January. Both have
separate germline, somatic clinical impact, and oncogenicity fields. Description
and free-text rationale are not compared in this phase: unchanged here does
not mean every field in the underlying assertion is unchanged.

Membership comes from exact BRCA1/BRCA2 gene tokens in the variant-summary
snapshots, **not** the optional `SubmittedGeneSymbol`. All submitted conditions
for these gene-overlapping variants are retained, including unspecified states,
without a clinical hereditary-cancer filter. This is a deliberately broad
technical scope, not a clinician-approved disease inclusion list. Clinical
review of the disease scope remains open before any clinical claims or pilot.

## Records and identity

ClinVar's [record guide](https://www.ncbi.nlm.nih.gov/clinvar/docs/ftp_primer/)
and [identifier guide](https://www.ncbi.nlm.nih.gov/clinvar/docs/identifiers/)
distinguish VCV variant aggregates, RCV variant–condition aggregates, and SCV
individual assertions. SCV base accession is the longitudinal key; its version
is separately retained. A version increase alone is not a changed classification.

This TSV does not contain stable submitter IDs, VCV versions, or explicit SCV–RCV
links. Those fields are **null**, not inferred. RCV lists in variant-summary
cannot be assigned to individual SCVs by positional or textual matching.
Reliable RCV aggregate comparisons and stable submitter identities require
future XML enrichment. The current comparison is condition-aware SCV comparison,
not a claim to implement an RCV aggregate comparator.

Raw `SubmittedPhenotypeInfo` and `ReportedPhenotypeInfo` remain authoritative.
Explicit MedGen IDs are extracted from the mapped field only as additional
references; no ontology equivalence is inferred. Different raw condition sets
or spellings are conservatively flagged as context changes. Multiple SCVs for
one lab/variant are never collapsed. Exact duplicate rows for a base SCV can be
collapsed with all source lines retained; conflicting alternatives are
`unresolved` rather than arbitrarily selecting the largest version.

## Event semantics

| Status | Meaning |
| --- | --- |
| `classification_changed` | Same SCV base, variant, submitter name, raw condition context and classification type; available germline value differs |
| `newly_observed` | SCV is only in the later selected snapshot |
| `missing` | SCV is only in the earlier selected snapshot; not proof of withdrawal/deletion/reclassification |
| `context_changed` | Variant association, raw condition context, submitter name or classification type differs; raw values retained but not treated as an uncomplicated same-context reclassification |
| `unchanged` | Available classification agrees; metadata/version flags can still differ |
| `unavailable` | A matched classification is not available for comparison |
| `unresolved` | More than one incompatible record for the same SCV base in a snapshot |

Flags independently record changed classification strings, conditions, submitter
names, variant identity, type, version, review status, last-evaluated date,
collection method, reported origin, and submitted gene. A renamed submitter may
therefore produce a context flag; without stable IDs it is not evidence that
ownership changed. Purely somatic assertions are excluded. A germline-to-somatic
transition is a context change rather than a spurious missing/new pair.

Every event preserves full selected old/new fields with source filenames, URLs,
SHA-256 hashes, source line numbers, and release dates. The event's
`observed_between` interval is separate from the raw last-evaluated assertion
dates; no exact publication day or intermediate events are inferred. Absences
must be investigated for source/filter coverage, identity transitions, replacement
or withdrawal before explaining them clinically.

## Reproduce without PostgreSQL or a UI

```sh
# From project root; original variant releases must also be present.
PYTHONPATH=src python3 scripts/download_releases.py
PYTHONPATH=src python3 scripts/download_releases.py --manifest docs/submission-releases.json
PYTHONPATH=src python3 -m brca_review.cli --genes BRCA1 BRCA2 --manifest docs/releases.json --output outputs/brca1-brca2.csv
PYTHONPATH=src python3 -m brca_review.submission_cli --output outputs/submissions.jsonl
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The aggregate CLI defaults to BRCA1 for backward compatibility. Its original
BRCA1 CSV remains byte-identical. The SCV CLI defaults to both genes and the
same two release dates; mismatched manifest dates are rejected. Optional
`--variants ID ID ...` limits the comparison to an explicit public-ID subset;
unknown/out-of-scope IDs fail instead of silently disappearing. Both full
submission archives total approximately 581 MB compressed, in addition to the
623 MB original variant files. Allow memory/disk for retained SCVs and JSONL.

These CLI outputs do not automatically replace the pinned Phase 1 web snapshot.
No database schema, application tables, migration, API server, or production
proxy is changed by Phase 2. See the [verification log](submission-verification.md)
for actual inspected examples and coverage limitations.
