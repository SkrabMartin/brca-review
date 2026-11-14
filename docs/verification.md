# Historical verification — BRCA1 aggregate comparison

Checked on 2026-11-13 by the implementation agent, not an independent clinical
reviewer. These are actual public ClinVar records, not synthetic fixtures.
The check independently opened the decompressed source rows by line number
without calling the application extractor, then inspected their Variation ID,
gene, classification, review status, assembly, and condition text. The resulting
values were compared with the CLI output. A separate human/clinical review is
still advisable before using these as portfolio clinical examples.

Exact source URLs and SHA-256 hashes are pinned in [releases.json](releases.json).
Line numbers below are one-based physical lines after decompression, including
the header. Both assembly rows were inspected; their aggregate values agree.

| Variation ID | Source | Lines (GRCh37, GRCh38) | Raw aggregate germline classification | Raw review status |
| --- | --- | --- | --- | --- |
| 37422 | January 2025 | 43739, 43740 | Uncertain significance | criteria provided, multiple submitters, no conflicts |
| 37422 | February 2025 | 43758, 43759 | Conflicting classifications of pathogenicity | criteria provided, conflicting classifications |
| 17660 | January 2025 | 32141, 32142 | Pathogenic | criteria provided, multiple submitters, no conflicts |
| 17660 | February 2025 | 32140, 32141 | Pathogenic | criteria provided, multiple submitters, no conflicts |

Expected and observed CLI status: **37422 changed**, **17660 unchanged**.
The names in both snapshots were `NM_007294.4(BRCA1):c.161A>G (p.Gln54Arg)`
and `NM_007294.4(BRCA1):c.190T>G (p.Cys64Gly)`, respectively. Names were used
for inspection only, never matching.

For 37422, the January condition list contains familial breast-ovarian cancer
susceptibility and hereditary breast ovarian cancer syndrome; February also
contains hereditary cancer-predisposing syndrome. These are variant-wide
lists, not proof of which condition/submission caused the aggregate change.
For 17660 the lists additionally include unspecified/not-provided conditions.
No condition-specific or clinical conclusion is assigned to either aggregate.

Current navigation: [37422](https://www.ncbi.nlm.nih.gov/clinvar/variation/37422/),
[17660](https://www.ncbi.nlm.nih.gov/clinvar/variation/17660/). Current pages are
not evidence of the historical values. Historical VCV versions were not
retrieved; the dated TSV rows are the evidence checked here.

## Independent row inspection

After downloading the pinned files, inspect source rows with standard tools:

```sh
gzip -cd data/variant_summary_2025-01.txt.gz | sed -n '1p;32141,32142p;43739,43740p'
gzip -cd data/variant_summary_2025-02.txt.gz | sed -n '1p;32140,32141p;43758,43759p'
```

## Full-release result

For publication dates 2025-01-02 → 2025-02-06:

| Status | Variation IDs |
| --- | ---: |
| changed | 46 |
| unchanged | 12,591 |
| newly_observed | 104 |
| unavailable | 2,229 |
| missing | 0 |
| unresolved | 0 |
| total union | 14,970 |

Missing/unresolved states are covered by synthetic tests because no such events
were observed in this pair. Two independent CLI executions must produce identical
CSV bytes; the README includes the reproducibility command. A raw string change
is not automatically new biological evidence or a clinical reclassification.

Verified output SHA-256: `db13a977ca45c52a405778bf78eaf187b0e595d893298660187ea20776b3bfb6`.
