# Data and validation documentation

- [Pinned release metadata](releases.json): exact URLs, dates, sizes, SHA-256 hashes, and observed headers.
- [Source selection and field mapping](release-manifest.md): TSV compatibility, comparison semantics, and scope limits.
- [Historical verification](verification.md): changed/unchanged public records and reproducible full-release counts.

Raw downloads stay in ignored `data/`; generated results stay in ignored
`outputs/`. SCV condition/source context is now retained by the file-only CLI; XML enrichment and clinical scope review remain open.
Phase 4 will add a reviewer benchmark and demo instructions. No patient data
belongs in this repository.

- [SCV comparison semantics and reproduction](submissions.md).
- [Pinned submission releases](submission-releases.json).
- [Historical SCV verification](submission-verification.md) and [inspected example fields](submission-examples.json).
- [PostgreSQL schema, migration/import workflow, and read-only API](storage.md).
- [Pinned input artifact hashes](comparison-artifacts.json).
- [React application containers and routing](frontend.md).

- [Phase 4 provisional benchmark, protocol, empty observation templates and demo](validation/README.md): preparation only; no human pilot or clinical validation results.
