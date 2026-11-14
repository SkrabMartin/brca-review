# Phase 2 historical verification

Checked 2026-11-13 by the implementation agent, not an independent clinical
reviewer. The independent check scanned the **complete decompressed files**
without using the application's gene filter, extraction, or comparison functions.
It inspected SCV/version, Variation ID, raw classification, submitted/mapped
conditions, submitter name, and last-evaluated dates. Selected aggregate rows
were separately read to verify unchanged aggregate classifications.

[Exact inspected fields and source line numbers](submission-examples.json)
are recorded alongside expected event types. Source hashes/URLs are in the
[submission manifest](submission-releases.json) and [variant manifest](releases.json).
Line numbers count the header and embedded submission-file preamble.

## Changed SCV, unchanged aggregate: BRCA2 91425

Ambry Genetics assertion **SCV000184021.8 → SCV000184021.9** changed from
`Uncertain significance` to `Likely benign`. Submitted condition remained
`MedGen:C0027672`, mapped to `C0027672:Hereditary cancer-predisposing syndrome`.
The old last-evaluated date is `Oct 18, 2022`; the new date is `Nov 26, 2024`.
The update was **observed between archive publication dates 2025-01-02 and
2025-02-06**, not asserted to have been published on the evaluation date.

Submission lines: January **250350**, February **253494**. Aggregate rows:
January **99662–99663**, February **99799–99800**. Both assemblies at both dates
have `Conflicting classifications of pathogenicity`. Thus a genuine submission
classification difference is present while the observed aggregate is stable.
This is historical record verification, not endorsement of a clinical conclusion.
Current navigation: [Variation 91425](https://www.ncbi.nlm.nih.gov/clinvar/variation/91425/).

## Second changed SCV, unchanged aggregate: BRCA1 141093

Ambry Genetics **SCV000184222.8 → .9** changed from `Uncertain significance`
to `Likely benign`, with the same submitted/mapped condition C0027672. Raw
last-evaluated dates: `Nov 16, 2020` → `Oct 02, 2024`. Submission lines:
January **377689**, February **382191**. Aggregate rows January **144934–144935**
and February **145075–145076** retain `Conflicting classifications of pathogenicity`.
Current navigation: [Variation 141093](https://www.ncbi.nlm.nih.gov/clinvar/variation/141093/).

## Controls and context change

| SCV | Variant | Verification |
| --- | --- | --- |
| SCV000030123.2 | BRCA2 9317 | Unchanged Pathogenic; OMIM; mapped condition C2675520; January line 41759, February 42752 |
| SCV005437124.1 | BRCA2 38235 | Newly observed; KCCC/NGS Laboratory, Kuwait Cancer Control Center; Pathogenic; OMIM:612555 → mapped C2675520; February line 112216; absent from the complete January scan |
| SCV000296299.2 → .3 | BRCA1 37574 | Context changed: Quest Diagnostics Nichols Institute San Juan Capistrano; Pathogenic remains Pathogenic, but submitted OMIM:604370 / mapped C2676676 changes to not provided / C3661900. January line 101628, February 103536 |

The last case must not be represented as a same-condition classification change.
No missing SCV or incompatible duplicate was observed in the selected full-gene
pair. Those states have labeled synthetic tests instead of fabricated historical
examples. Missing does not imply deletion: a future real case needs coverage,
accession/replacement, or withdrawal investigation before explanation.

## Reproduce inspection

After downloading and checksum-verifying both pinned submission archives:

```sh
gzip -cd data/submission_summary_2025-01.txt.gz | grep -F 'SCV000184021.'
gzip -cd data/submission_summary_2025-02.txt.gz | grep -F 'SCV000184021.'
# Expected no match (exit 1) in the older snapshot:
gzip -cd data/submission_summary_2025-01.txt.gz | grep -F 'SCV005437124.'
```

Use the recorded source lines for variant-summary inspection; current ClinVar
pages are navigation aids, not historical evidence. Full XML or VCV-version
cross-validation is not claimed. Stable submitter IDs and SCV–RCV linkage
remain unsupported by this source.

## Full-scope results

Aggregate BRCA1 + BRCA2 union: **34,356** Variation IDs; 113 changed, 31,633
unchanged, 352 newly observed, 2,258 unavailable, zero missing/unresolved.
The original BRCA1-only output remains byte-identical to Phase 1.

SCV comparison: 111 classification changes at stable raw context, 92 context
changes, 1,405 newly observed SCVs, 4,654 unavailable matched classifications,
108,472 unchanged classifications, zero missing/unresolved. Total: **114,734**
SCV bases, excluding assertions that are purely somatic on both sides. Unchanged
classifications can still carry metadata/version flags. Context changes can
include spelling or normalization differences; they are not necessarily new
biological evidence. Gene membership does not establish disease relevance.

Two full SCV CLI executions were byte-identical (`cmp` passed). JSONL SHA-256:
`08099d0a5f3639151b3c80c043335dbbbfd6b8e0efbe007cd5f538d29eac3bd5`.
