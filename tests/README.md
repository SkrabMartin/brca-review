# Tests

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` without installing
storage dependencies or starting Docker. Fixtures in `test_comparison.py` are
synthetic, not historical examples. They cover event states, numeric ID order,
compatible duplicate rows, conflicting classifications, exact gene tokens,
checksum/header rejection, and review-only changes.

The separate [historical verification log](../docs/verification.md) documents
actual public records checked against dated source files. Full-data output is
reproduced using the commands in the root README; downloads and outputs stay
ignored. Synthetic SCV tests now cover changed/new/missing/unavailable/context-changed assertions, versions, ambiguous duplicates, source preservation, BRCA2 membership, and end-to-end CLI provenance/date/scope checks.

Optional Phase 3 tests in `test_storage_review.py` use real PostgreSQL rather
than SQLite. Install the pinned web/test dependencies and configure a disposable
migrated/imported `brca_review_test_*` database, with `BRCA_TEST_DATABASE` matching
its name; see `docs/storage.md`. Without those dependencies/configuration these
checks skip while the eight file-only tests remain runnable with `python3 -S`.
Frontend behavior is covered by `cd frontend && corepack pnpm test`.
