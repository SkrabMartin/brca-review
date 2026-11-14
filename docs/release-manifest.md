# Phase 1 data sources and field mapping

ClinVar is the data source. Archive discovery and retrieval: 2026-11-13.
The machine-readable [manifest](releases.json) pins exact URLs, compressed-byte
SHA-256 hashes, sizes, release dates, retrieval dates, and full observed headers.
These are computed local SHA-256 hashes, not claimed publisher signatures.

## Selection

The official [TSV archive](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/archive/)
contained both `variant_summary_2025-01.txt.gz` (288,267,418 bytes, published
2025-01-02) and `variant_summary_2025-02.txt.gz` (334,887,755 bytes, published
2025-02-06). Both complete files were downloaded. January has 40 columns and February has 43. The first 40 headers match;
February appends `SCVsForAggregateGermlineClassification`,
`SCVsForAggregateSomaticClinicalImpact`, and
`SCVsForAggregateOncogenicityClassification` (not used by this comparison).
The required comparison columns have identical names and documented meanings.
Release dates refer to archive publication dates, not individual evaluation
dates or a verified exact cutoff time for every included assertion.

[VCV XML](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/) also lists matching
monthly files, but these are substantially larger (about 4.2 and 4.6 GB
compressed). XML was not downloaded for Phase 1: the TSV contains the required
variant aggregate fields. VCF has partial coverage and is unnecessary here.
The rolling `variant_summary.txt.gz` is not used as a historical release.

There is no explicit TSV schema version in the header. Our adapter format
`clinvar-variant-summary-tsv-v1` identifies this application mapping, not an
NCBI schema version. Exact header equality is enforced against each manifest
entry. See [ClinVar's file guide](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/README),
[data-access documentation](https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/),
and [record guide](https://www.ncbi.nlm.nih.gov/clinvar/docs/ftp_primer/).

## Mapping and scope

| Source | Use |
| --- | --- |
| `VariationID` | Positive numeric stable comparison key; never join on row order, HGVS, AlleleID, or coordinates |
| `GeneSymbol` | Exact comma/semicolon-delimited token `BRCA1`; includes multigene overlaps, whose gene set is retained |
| `ClinicalSignificance` | Raw variant-level aggregate **germline** classification; preserve the entire string, including composite terms |
| `ReviewStatus` | Raw aggregate germline review status, retained on both sides |
| `Assembly` and repeated rows | Do not pick a preferred assembly; collapse compatible values by Variation ID and preserve source line numbers |
| `LastEvaluated` | Not used as publication date; describes evaluation timing, not when a difference entered ClinVar |
| `SomaticClinicalImpact`, `Oncogenicity` | Never used for this germline comparison |
| `PhenotypeIDS`, `PhenotypeList`, `RCVaccession` | Not interpreted as a one-to-one aggregate/condition mapping; condition-aware output belongs to Phase 2 |
| VCV/SCV accession versions | Not available in this TSV; not fabricated. Stable Variation ID plus the dated file/hash and source lines identify this snapshot |

The file guide explicitly describes `ClinicalSignificance` as aggregate germline
classification and `ReviewStatus` as its review status. This phase reports
BRCA1 gene-overlap aggregates, not a clinically approved hereditary-cancer
condition subset. It does not filter by `Origin` because the classification
column already distinguishes germline from somatic classification categories.
It does not infer an individual person's allele origin.

## Comparison contract

Output is sorted numerically by Variation ID. JSON arrays inside CSV preserve
raw classification/review values, gene sets, and all source line numbers.
No classification spelling, case, whitespace, or composite-term order is
normalized; a raw-value change may be nomenclature rather than new evidence.

Repeated rows with one classification and one review status are compatible.
Contradictions in either are `unresolved`, with all alternatives retained.
Different gene sets are retained as their union. Matched unavailable values
(empty, `-`, `na`, `not provided`, `no classification provided`, case-insensitive)
are `unavailable`, even if equal. Other unfamiliar terms remain raw values.
Review-status-only changes remain classification `unchanged`, visible in their
own old/new columns. Presence in one release only is `newly_observed` or
`missing`, never an inferred clinical reclassification or deletion.

TSV does not reliably resolve merged/redirected identities. Do not join IDs
based on similar names: new/missing IDs require manual identity review.
No submission changes, condition specificity, or clinical conclusions are
claimed. Every output row links to both dated sources; the convenient ClinVar
variant link opens a current page and is not historical evidence.
