# Reviewer pilot protocol, version 1 — not yet executed

## Question and scope

Does BRCA Review help qualified clinical geneticists/variant curators find the
specified published changes more quickly and accurately than a named ClinVar
review workflow for the **same 2025-01-02 → 2025-02-06 interval**? The unit is a
public record-review task, not a patient or a new pathogenicity assessment.
No inference about patient outcomes follows from this feasibility pilot.

This convenience sample is deliberately enriched for differences and controls;
it is not a random sample or an estimate of ClinVar change prevalence. The
[reference](benchmark.json) contains 16 cases, eight per gene, and 21 tasks:
16 aggregates (four changed, eight unchanged, two newly observed, two unavailable)
and five SCVs (two changed with stable aggregate, one new, one context change,
one unchanged). No real missing/incompatible-duplicate event was observed in the
selected pair; those behaviors remain synthetic software checks outside human
benchmark scoring. Do not manufacture a real missing example.

Clinical disease inclusion has not been approved. In particular, **C06 (3393452)**
lists only Fanconi anemia in the source: it is retained as an explicit technical
scope challenge, not assumed to be a hereditary-cancer example. The
[scope-review sheet](scope-review.csv) leaves every inclusion decision pending.
A clinician must approve or exclude it under a new frozen version before a
clinically scoped pilot. C05 and several other cases have mixed/unspecified
conditions, illustrating why a gene filter alone is insufficient. Keep all raw submitted/mapped
condition context, including unspecified conditions. Do not collapse a variant
aggregate into a single disease, equate names by intuition, or infer missing
SCV–RCV links/submitter IDs/VCV versions. Source-level correctness and disease
relevance require independent review before recruitment.

## Gates before a pilot

1. Independent qualified reviewer checks every task's old/new evidence and
   gene/condition scope against dated sources, using the review-log template.
   Resolve disagreements; preserve exclusions/reasons. Freeze an approved
   version with hashes and a dated adjudication record. Current reference is
   agent-prepared and pending, not approved ground truth.
2. For **each task** verify the proposed control workflow exposes both historical
   values and, for SCV tasks, the accession/version, submitter, condition and
   evaluation date. Record navigation steps, access failures and required versions.
   A current VCV page or HTTP200 is insufficient. Do not assume that an accession
   version equals a release date.
3. Freeze one named baseline, task set, outcome definitions, timeouts/exclusions,
   app commit/build, source hashes, browser/device, order assignment and instructions
   before seeing response outcomes. Never silently remove difficult cases later.
4. Recruit qualified reviewers and obtain their voluntary agreement to the
   evaluation and its data handling. Use pseudonymous codes.

## Control workflows — keep conclusions separate

**Direct ClinVar web (`clinvar_web`)**: normal ClinVar pages/history, without
BRCA Review or this reference sheet. Must pass per-task historical-access checks.
The automated check on 2026-11-14 encountered a browser-verification page; no
historical values were verified through that page. This is a limitation of this
probe, not proof that humans cannot access record history. Direct-web baseline
is currently **not approved** and no comparative time claim is enabled.

**ClinVar archive-assisted (`clinvar_archive`)**: official full dated TSV files,
publisher documentation and a neutral text/table viewer, plus current ClinVar
pages for orientation if desired. Allow both methods the same full historical
sources and condition/SCV information, but no app diff, app output or answer key
in the control. Freeze any extraction/navigation helpers and setup time rules
before testing. This evaluates an archive-assisted workflow, not direct ClinVar
website review. The archive reachability/local hashes are technically verified;
independent review and pilot source usability remain pending.

Run a short untimed technical navigation trial first. If a web task is inaccessible,
record it, leave direct-web gate closed, and either predefine a comparable subset
under a new frozen version or use the separately named archive-assisted baseline.
Do not attribute inaccessible-control time to an app speed improvement.

## Participant instructions and order

Use [tasks.csv](tasks.csv) and only public identifiers. Do not show reference.csv,
benchmark.json, example answers or scorer test results until the participant's
sessions are complete. Public availability of the answer key is a possible
contamination source: ask about prior exposure and report it.

Use both methods on the same frozen tasks; allocate approximately half the
reviewers to app-first and half baseline-first. Prepare deterministic but different
case orders for the two sessions and record the actual order. Schedule a declared
washout where feasible; no interval guarantees removal of recall. Do not use the
same cases for training. Record order effects and interpret any apparent benefit
cautiously. An alternative disjoint matched-block study needs a new protocol and
scoring denominator rather than silently applying this full-task scorer.

For each task: identify the specified aggregate or SCV's event type, copy previous
and current classification, and give the requested condition/submitter/accession/
evaluation context only where applicable. For a variant-wide aggregate those SCV
fields are not applicable. Return published values, not your own clinical judgment.
Unknown/absent data must not be filled from memory or a current-only page.

## Observation recording

Copy header-only templates to ignored `outputs/validation/`. Participant codes
use letters/digits/underscore/hyphen only (max 32), not names. Every response must
declare `record_kind=human` or `synthetic`; tests/dry runs must be synthetic.
Methods are exactly `app`, `clinvar_web`, `clinvar_archive`. Never merge them.
One row per participant/method/task; duplicates require adjudication rather than
selecting a favorable answer. Include fixed Variation ID and SCV base for SCV tasks.

`completion`: `complete`, `timeout`, or `not_assessable`. Complete rows use the
published status enum from the reference contract: `changed`, `unchanged`,
`newly_observed`, `unavailable`, `missing`, `unresolved` for aggregate tasks;
SCV tasks additionally use `classification_changed` and `context_changed`.
Incomplete rows leave status blank. Inaccessible records are not an `unavailable`
classification: `unavailable` describes a source value, `not_assessable` describes
a failed review task. Unanswered expected tasks remain in denominators.

Aggregate classifications can be copied as JSON string arrays (including `[]`
for absence); SCV classification fields are raw strings. Preserve composite terms.
For condition fields copy the **mapped condition** or its full explicit MedGen
ID set; submitted-condition text remains in reference evidence for adjudication.
The scorer accepts exact explicit MedGen ID sets, not inferred semantic aliases.
Classification/name/date/accession fields allow whitespace/case differences only;
this is response transcription tolerance, not changed ingestion semantics.

Record gross elapsed time and any excluded time with a reason. Never subtract
reading, navigation or ordinary source lookup time. Predeclare handling of outages,
interruptions and task timeout (suggested pilot cap: 10 minutes/task; fix the final
cap after untimed navigation and before recruitment). Keep timed-out/inaccessible
tasks and analyze them, not as successful fast reviews. Per-task time is optional
if batch work prevents unambiguous allocation; do not double count shared navigation.
Primary batch time comes from an independently recorded session timer, not a sum
of optional task times. Report gross and net times and all exclusions.

## Scoring and analysis

An expected positive event is one of `changed`, `newly_observed`, `missing`,
`classification_changed`, or `context_changed`. There are **10 positives** in
this frozen task set and 11 control tasks. A true positive requires correct task
level, variant, SCV identity when applicable, and event type. A positive claim
with wrong type/identity is a false positive and leaves the actual positive missed
(false negative). Wrong positive claims on controls are false positives.

Report TP/FP/FN, precision=TP/(TP+FP), recall=TP/10, exact status accuracy across
all 21 tasks, missing/inaccessible/timed-out counts, and per-field old/new accuracy
for classifications, conditions, submitters, accession versions, evaluation and
release dates. Null precision with no positive claims is undefined, not perfection.
Field errors remain separate even if event detection was correct. Nonapplicable
fields are excluded from attribute denominators; missing applicable fields fail.

Analyze each reviewer as the paired unit, not 21 supposedly independent human
observations. A net time saving is baseline batch seconds minus app batch seconds.
Report raw paired results, median savings, accuracy/precision/recall differences
and comments with participant count/order. Do not infer a useful speed gain from
lower time accompanied by lower accuracy, timeouts, inaccessible controls or
incomplete tasks. Small samples support descriptive feasibility only.

The scorer refuses timing eligibility unless the reference has documented
independent approval, the chosen baseline gate is enabled, both complete sessions
verify source access and share the same declared order, and neither method has
missing/timed-out/not-assessable tasks. Synthetic observations are excluded from
human counts/timing summaries. The current reference gates are false. The scorer
never emits an automatic clinical/usefulness conclusion; interpretation requires
review of actual observations and limitations.

## Completion and reporting

Report participant count, raw observations, exact reference/protocol/build hashes,
source-access problems, disagreements, exclusions and analysis. A negative result
is legitimate. With no participants, report preparation/technical validation only.
Current participant count is zero and there are no reviewer outcome measurements.
