# T08 prospective robustness and engineering selection record

Frozen **2026-10-26 before any T08 candidate comparison**. Design worker requested
GPT-6.1 Sol / Medium / Standard; effective model not exposed. Coordinator owns PLAN,
review and commits. This document authorizes the bounded implementation/run plan below;
it does not record successful experiments that have not happened.

## Independent benchmark gate: none validated in this bounded review

Exactly two provider repositories were investigated, with their documentation and history.
No other-match assets were downloaded, no new dependencies installed, and no supplied-match
annotations opened. These findings do not imply that no suitable benchmark exists.

### Source 1: Metrica Sports sample data — reject for this experiment

[Provider README, immutable revision](https://github.com/metrica-sports/sample-data/blob/e706dd506b360d69d9d123d5b8026e7294b13996/README.md),
[revision](https://github.com/metrica-sports/sample-data/commit/e706dd506b360d69d9d123d5b8026e7294b13996)
(2021-04-15), inspected 2026-10-26. Public access also permits organizer inspection.
Sample Games 1/2 are anonymized; Game 3 is an additional sample. Real team/match identities
and independence from the competition match are not certified here. Tracking and events
are synchronized. Games 1/2 use normalized top-left-origin coordinates and a 105 x 68 m
pitch; Game 3 uses FIFA EPTS tracking/metadata and JSON events. The README requests source
credit for public use; it does not establish a comprehensive data redistribution licence.
Team mapping, FPS/timestamp conventions, missingness rates and label-production procedures
were not validated. No exhaustive controlled-possession/dead-ball reference is established
by that README. The linked event definitions PDF could not be parsed by the web tool.
Events alone cannot fill the unannotated timeline. No acquisition or split follows.

### Source 2: SkillCorner open data — reject as a validated reference here

[Provider README, immutable revision](https://github.com/SkillCorner/opendata/blob/c1e17a0cc3e07e1774b52d929c1a0b85115143fc/README.md),
[revision](https://github.com/SkillCorner/opendata/commit/c1e17a0cc3e07e1774b52d929c1a0b85115143fc)
(2026-08-07), inspected 2026-10-26. Ten 2024/25 Australian A-League matches are described,
separate in competition from this challenge. Individual IDs/teams were not acquired.
Public access supports organizer inspection. Broadcast computer-vision tracking supplies
10 fps frames, tenth-second timestamps, periods 1/2, metre coordinates centered on the
pitch, possession player/group (home/away), and player detection/extrapolation flags.
Dynamic Events and live-only phase intervals are derived products. Exact missingness,
null-group meaning, exhaustive live coverage, controlled-touch/deflection conventions,
and independent reference validation were not established. Thus absent phases cannot
be converted automatically to D. The linked phase specification PDF was inaccessible.
Automatic labels are not inherently unusable; their compatibility as ground truth is
unverified here. No acquisition or split follows.

The [repository MIT licence](https://github.com/SkillCorner/opendata/blob/master/LICENSE)
permits software/documentation reuse and redistribution with its notice; the README also
requests provider credit. A separate explicit data-specific grant was not established in
this review; no data redistribution is planned. This legal uncertainty is additional to,
and does not replace, the annotation-semantics rejection.

I03 remains open. There is no development/holdout score or match split. Continue the
synthetic and engineering path in [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md).

## Frozen code, configurations and hypothesis

Base code commit: **c9d9a7dc1d8af9bf79e305ca6164db2b6cb0548e** (T07).
Implement only fixture/runner/report code for T08; record its tree digest or subsequent
checkpoint before running. Do not alter decoder defaults, feature logic, existing tests,
T04 fixtures, official validator/evaluator or pinned dependencies to improve results.
No RNG is required: seed **not applicable, deterministic analytical fixtures**.

At most **three total configurations**, including the unchanged default:

| ID | temporal.Config values | T06 | Hypothesis |
|---|---|---|---|
| C0 | radius=2 m; margin=0.5 m; confirmation=0.4 s; speed ceiling=12 m/s; retention=3 s | unchanged defaults | Initial sustained-control proxy bridges short gaps and rejects short contacts. |
| C1 | C0 with `control_seconds=0.01` only | unchanged | Minimal supported confirmation admits two-frame contacts and exposes the value/cost of persistence. |
| C2 | C0 with `retain_seconds=0.01` only | unchanged | Almost no carry exposes gap fragmentation and the benefit/cost of finite ownership memory. |

Use the existing public API `predict(inputs, Config(...))` or
`infer(features, Config(...))`. The 0.01 s alternatives preserve Config's positive-value
contract. C1 is **not zero-frame confirmation**: `_confirm_runs` requires at least one
elapsed frame/two observations. At 10 fps C2 retains no unsupported next frame. No combined
ablation, threshold sweep, new state model or alternative seed is authorized.

The comparison is explanatory engineering evidence, not a ranking of real-match accuracy.
The known failure mechanisms include proximity without touch, unsupported in-pitch/missing
ball stoppages (I04), and X extending stale ownership under the official spell metric.

## Fixture specification v1 (freeze before implementation/runs)

Add `evaluation/robustness_cases.py` and focused `tests/test_robustness.py`; reuse the
immutable `Inputs/Observation/Player/Phase/Case/Interval` schema and existing shared feature
builder. Keep expected arrays separate from predictor inputs. Do not import helpers from
`tests/test_temporal.py` or derive expectations from predictor outputs. Every interval
below is half-open, expressed in seconds and converted exactly at 5/10/25 fps. Unless
stated otherwise use 10 fps, a 100 x 60 m pitch and half=1; `t=i/fps`, ball=(20+t,25),
controller=(19.7+t,25), opponent=(20+t,45). At each team change exchange which team has
these two player positions. Reindex all frames consecutively after transformations.

| Fixture | Independent expectation / assertion |
|---|---|
| R01 sustained + controlled turnover | Duration 10 s; controller H before t=5, A thereafter. Labels H [0,5), A [5,10). |
| R02 two-frame deflection | Duration 8 s; H controls except [3,3.2), where A takes the near-player position and H is 20 m away. Intended touch is a deflection, no control: H throughout. C1 is expected to violate this contract; report actual failures without weakening it. |
| R03 short occlusion | R01 with missing ball [3,4). Expected remains H [0,5), A [5,10). Missing never implies D. C2 is expected to fragment H with X. |
| R04 long unsupported interval | Duration 10 s; H near-ball geometry throughout; ball missing [2,8). Expected H [0,5), X [5,8), H [8,10) at 10 fps. Last direct evidence t=1.9; retention includes t=4.9, expires t=5. This is an uncertainty-policy contract, not a label for real loose play. |
| R05 fresh restart | Duration 10 s; H controls [0,3); visible ball fixed at (23,-2) [3,6); A controls [6,10). Expected H/D/A at 3 and 6 s. No restart tag boundary enters expectations. |
| R06 half reset under missingness | Duration 10 s; H controls [0,4); half changes at 4; ball missing [4,6); A controls [6,10). Expected H [0,4), X [4,6), A [6,10). |
| R07 bounded observation noise | R01 plus ball-only deterministic noise `(0.04*(-1)^i, 0.03*(-1)^(i//2))` m. Expected unchanged H/A. Run only at 10 fps to bound apparent noise speed. |

R01/R03/R05/R06 also run at 5 and 25 fps using the same continuous-time formula and
second boundaries; require exactly the same intended second boundaries. R04 remains
10 fps because endpoint-inclusive finite memory has explicit sampling semantics. R02
remains a two-frame 10 fps contact, rather than changing its physical duration silently.

Run these fixed metamorphic checks for **each** configuration, reporting equality failures
separately from its semantic contract failures:

- Swap H/A in players and phase team fields in all seven fixtures; require H/A-swapped
  outputs and unchanged D/X. Reverse player slot ordering; require equal outputs.
- Prepend 2 s of empty observations with half=0 to R01/R03/R05/R06 and shift/reindex the
  original geometry (do not restart the trajectory formula); require the original output
  suffix unchanged and prefix X. This tests time translation without carrying prior state.
- Convert all R01/R05 metre positions to normalized x/100,y/60 and back through the shared
  `_normalized_to_pitch_m` helper; require feature distances/speeds equal within 1e-12 and
  exactly equal labels. This tests conversion, **not scale invariance**: physical thresholds
  must stay in metres; changing pitch size and all geometry is a different problem.
- Decode every fixture twice with fresh calls; compare all Result arrays (including direct
  control/dead-state/assessed arrays), not just labels. Never use a candidate's output as
  the semantic expectation; paired output is valid only for the stated invariance.

### Mandatory limitation witnesses; do not roll into a blanket PASS

L01: 8 s at 10 fps; ball fixed at (20,25); H=(19.7,25), A=(20,45), no phases.
Author two scenario intents over these identical inputs: (a) live H throughout,
(b) referee stoppage D throughout. Report raw agreement with each intention separately.
At least one must fail because no referee evidence differs. The current proxy is expected
to output H for both and therefore **fail the D intent**. This is a measured artificial
coverage limitation, not evidence that H is a valid stoppage prediction.

L02: H live control [0,2), then ball unavailable [2,8), all player geometry continuing as
above; intent is an in-pitch stoppage D [2,8). Report semantic disagreement with D, X
expiry and whether D was ever established. Do not force D from missingness or pretend
that X repairs the missing stoppage. Keep I04 open regardless of contract results.

Both witnesses intentionally lack identifying observations; their failures are disclosed
separately and cannot be cured by invented tags, answer-bearing fixture fields or tuning.
They are not acceptance contracts requiring an impossible simultaneous H/D answer.

## Acceptance, bounded execution and selection (prospective)

Run ID **T08-E01**. All result fields are **PENDING** at preregistration.

1. Freeze fixture/runner source digest (SHA-256 of sorted path/content manifest) and record
   Python/NumPy versions before executing candidates. A digest may identify uncommitted
   code; coordinator can subsequently commit that exact verified source. Add fixtures to
   the unit suite; existing 74 tests must pass unchanged. Fixture structure tests may run
   before candidate comparisons. No supplied/public labels or score APIs may be imported.
2. Run exactly C0/C1/C2 once against the eight unchanged T04 contracts, R01–R07 variants,
   metamorphic checks and L01/L02. Each semantic contract passes only with zero raw-label
   mismatches. Publish synthetic case pass/fail and mismatch counts; report witness failures
   explicitly. No F1, win totals disguised as accuracy, or thresholds chosen from results.
   All decoder-state invariances must pass. Do not assert that C1/C2 must pass semantic
   contracts: their informative failures are the intended ablation result.
3. Engineering resource checks: each config decodes one analytical 199,319-frame, 25 fps,
   two-player sequence with x=20+5*sin(t/10), ball=(x+.3,25), H=(x,25), A=(x,45), no RNG.
   Count feature construction separately from decode with `time.perf_counter`; use a fresh
   child process per config, standard-library `resource` for peak RSS (Darwin bytes; Linux
   KiB), no new dependency. Bound each process by 120 s wall time and 1 GiB peak RSS;
   report environment and synthetic times/RSS. These limits are engineering usability
   gates, not model-quality evidence. A timeout/resource failure stops that candidate,
   records failure and requires coordinator reassessment; no repeated performance loop.
4. For each config passing interface/determinism/resource checks, optionally reuse **one**
   existing local feature-cache load to run two independent full-match decodes. Require
   equal Result arrays and exact CSV bytes, valid H/A/D/X, X outside assessed positive-half
   blocks, D iff T06 DEAD, official frame range/row count, unchanged validator success on
   both exact files. Save only under checked ignored/untracked `data/predictions/t08/`;
   capture validator stdout/stderr and all exceptions. Return only fixed PASS/FAIL for
   production checks. No arrays, label counts/durations, hashes, per-frame failures,
   restricted reconstruction, public GT, evaluator calls or candidate scores in output.
   Full-match format checks are required for the selected release candidate, optional
   for rejected ablations. Reuse T07 safe writer/path guards; do not relax them.
5. Decision rule without independent labels: reject any candidate violating an unchanged
   T04 contract, R01–R07 semantic contract or invariance, interface, determinism, resource
   or selected full-match format gate. Known unidentifiable L01/L02 limitations are reported
   and remain release risks. Among eligible candidates choose the simplest passing,
   reproducible engineering method. Prefer C0 when eligible: C1/C2 change only constants,
   add no structural simplification, and have no independent quality evidence. If C0 fails
   a new identifying contract, stop and report; do not automatically select an ablation or
   revise fixtures/defaults. Any substantive repair/new configuration needs a new recorded
   Sol design decision. Two unsuccessful repair attempts trigger reassessment under AGENTS.
6. Add a compact public-safe results table to this file (code/digest, config, fixture v1,
   deterministic/no RNG, synthetic contract and invariance outcomes, L01/L02 failures,
   runtime/RSS, production fixed pass/fail, decision/limits). Preserve this prospective text
   and log failed/interrupted attempts before any repair. Coordinator updates PLAN/commits.

Planned implementation command interface: add `scripts/run_robustness.py` with a default
asset-free synthetic mode and an explicit `--full-match` option, and focused tests for
result accounting, expected ablation failures, digest stability, no unsafe file output and
sanitized production failures. The default command must not invoke full-match loading.
Example next-worker sequence (implement these commands before invoking them):

```bash
MTAH_DATA_DIR=/nonexistent .venv/bin/python -m unittest discover -s tests -q
MTAH_DATA_DIR=/nonexistent .venv/bin/python scripts/run_robustness.py
.venv/bin/python scripts/run_robustness.py --full-match
```

The full-match flag may first run the bounded synthetic comparison if its exact source
digest/config results are not already recorded locally; cache them to avoid a duplicate
comparison. Do not read ignored report contents into LLM context; report synthetic evidence
in the versioned summary and production pass/fail only. No acquisition, video inference,
training or public-window candidate scoring is part of this run.

## T09 decision

Keep T09 **DEFERRED**. I04 is a real evidence gap, but no independent reference or validated
referee/restart signal presently supports a broadcast method change; I01 synchronization
also remains unresolved. This review provides no reason to add GPU/video dependencies,
paid compute or unbounded detector experiments. T10 can package the honestly limited
tactical CPU method after T08. Future T09 activation requires a separate specific hypothesis,
observable validation target and synchronization/resource plan, recorded by the coordinator.

## Execution results

### Attempt 1 — incomplete implementation, superseded by one focused repair

The first implementation froze source digest
`8e331b9789997f8ff104fa0b05d5b3bca4048aad61eb6f2cc955d123b11299d4` and produced the
results recorded below. Coordinator review found that R05/R06 fps coverage was incomplete,
R02 did not place its contact at the preregistered coordinate, L01/L02 ran only under C0,
team-swap/time-prefix invariance accounting was incomplete, and the report cache did not
persist resource evidence or validate all path/runtime fields. Therefore the implementation
attempt is **INCOMPLETE** despite its passing checks; those results are retained as historical
evidence and are not the final T08 gate. Next action: repair fixture/runner/test accounting,
freeze a new digest, then run one corrected matrix and CLI full-match check. No decoder,
defaults, T04 fixture or expectation change is authorized.

Run **T08-E01**, 2026-10-26. Source digest frozen before comparisons:
`8e331b9789997f8ff104fa0b05d5b3bca4048aad61eb6f2cc955d123b11299d4` over sorted decoder,
feature, fixture, runner and test sources. Environment: Python 3.12.1, NumPy 2.4.4,
macOS 14.5 arm64. Deterministic analytical fixtures; no RNG. Fixture version 1 and the
preregistered configs above were used without edits. The existing 74 tests passed unchanged;
the full asset-free suite passed 78 tests before the candidate run.

| Configuration | T04 contracts | R01–R07 variants | Invariance failures | Feature / decode seconds | Peak RSS | Engineering eligibility |
|---|---:|---:|---:|---:|---:|---|
| C0 | 8/8 pass | 11/11 pass | 0 | 0.613 / 1.027 | 227,311,616 bytes | Eligible |
| C1 | 8/8 pass | 10/11 pass; R02 has 2 mismatches | 0 | 0.611 / 0.833 | 227,934,208 bytes | Rejected by preregistered R02 contract |
| C2 | 4/8 pass; failures are missing-ball, loose-ball, transient-deflection and turnover-after-gap contracts | 6/11 pass; R02, R03 at 5/10/25 fps and R04 fail | 0 | 0.724 / 1.306 | 225,820,672 bytes | Rejected by unchanged contracts |

All resource child processes passed their 120-second and 1-GiB limits. Invariance checks
covered home/away swaps, reversed player slots, repeated full Result arrays, applicable
empty-prefix time translations, and metre-normalization round trips. The full-match selected
C0 gate returned fixed **PASS**: two independent decodes matched across all Result arrays,
the exact CSV bytes matched, timeline/label/state invariants held, and the unchanged official
validator accepted both files. Outputs remain under ignored `data/predictions/t08/`; no
validator diagnostics or production-derived counts/hashes were surfaced.

Known-limit witnesses are reported separately from acceptance: L01 agrees with the live-H
intent (0 mismatches) and fails the indistinguishable stoppage-D intent (80/80); L02 fails
the requested in-pitch D interval (60/60), emits X after retention expiry, and never
establishes D. I04 remains open.

Historical decision from attempt 1: retain **C0** as the simplest eligible, reproducible
engineering method. This is not a claim that C0 improves possession quality or ranking; no
public labels/evaluator, private ground truth, model ranking, tuning, or checkpoint selection
were used. Attempt 1 required an infrastructure repair, so its “no repair” outcome is
superseded. T09 remains deferred. Attempt 2 results will determine whether T08 gates pass.

Repair check 1 failed before the candidate matrix: the focused structural test still looked
up the old unsuffixed R06 fixture after fps variants were added. No model comparison or
resource run occurred in this failed check. Next action: update that test to select the 10-fps
R06 variant, then rerun the asset-free suite.

### Attempt 2 — corrected implementation and final fixed run

The stale R06 assertion was corrected; the asset-free suite then passed **86 tests**. The
source digest was frozen before the matrix as
`6395f8fc7ccd7e96733c71cf425f5aee026c594a59381d343a84bdbe11cb10e7`, now including the
T04 harness, submission safety code and unchanged validator source. Runtime remained Python
3.12.1 / NumPy 2.4.4 on macOS 14.5 arm64. No source changed after this digest.

| Configuration | T04 contracts | R01–R07 variants | Invariance failures | Feature / decode seconds | Peak RSS | Engineering eligibility |
|---|---:|---:|---:|---:|---:|---|
| C0 | 8/8 pass | 15/15 pass | 0 | 0.537 / 0.865 | 223,838,208 bytes | Eligible |
| C1 | 8/8 pass | 14/15 pass; R02 has 2 mismatches | 0 | 0.536 / 0.723 | 235,241,472 bytes | Rejected by preregistered R02 contract |
| C2 | 4/8 pass | 10/15 pass; R02, R03 at 5/10/25 fps, and R04 fail | 0 | 0.533 / 0.727 | 240,025,600 bytes | Rejected by unchanged contracts |

Each isolated resource run passed the 120-second and 1-GiB limits. Home/away metamorphisms
checked swapped labels and control codes with assessed/dead state unchanged. Slot reversal,
all-array repeat determinism, applicable prefix shifts across every Result array, and R01/R05
metre round trips all passed for every configuration. Each configuration separately ran both
L01 intents and L02: live-H matched (0 mismatches), the indistinguishable stoppage-D intent
failed (80/80), and the missing-ball stoppage-D interval failed (60/60) while X expiry was
present and D was never established. These known limitations remain outside the acceptance
gate and I04 stays open.

The actual `.venv/bin/python scripts/run_robustness.py --full-match` command loaded and
validated the complete same-digest/runtime/config cache, did not repeat resource children,
and returned fixed **PASS** for selected C0: independent result arrays and CSV bytes matched,
timeline/label/state invariants held, and the unchanged validator accepted both files. Only
fixed PASS/FAIL was emitted for production checks; both CSVs remain under ignored
`data/predictions/t08/`. The asset-free default was separately covered by a test that verifies
it never invokes full-match loading. Cache path, atomic-write, truncated-result and gate tests
passed; private cache content was not exposed.

Final T08 decision: retain **C0** as the simplest eligible reproducible engineering method.
There is no real-match quality or ranking claim and no use of public labels, evaluator APIs,
private ground truth, training or tuning. Attempt 1 is retained above as incomplete historical
evidence, including its original digest and outcomes. T09 remains deferred; T10 may proceed
with I03/I04 and these limits disclosed. The private synthetic cache remains ignored and is
not a release artifact.

### Attempt 3 — focused Sol reassessment before rerun

Two Luna infrastructure attempts left cache/accounting defects despite passing candidate
runs. Before any further run, freeze a narrow repair: require the complete preregistered
invariance keyset and internally consistent nonnegative mismatch counts; reject traversal
and every cache destination except the exact ignored file; stop the command on any
configuration's resource failure; return only bool from the production helper. Remove
unused model execution from the fixture module. Add cache, resource-gate and path
regressions. Review full-match timeline/mask, repeated-array/byte equality and captured
validator output. No model, default, source gate or fixture expectation changes; this is
infrastructure repair, not method tuning. Prior results remain historical until final
source digest, asset-free suite, one corrected matrix and one cached production CLI pass.

Pre-run verification: **91 asset-free tests PASS**. Added explicit full-match mock
regressions for duplicate timeline IDs, assessed-mask mismatch, unequal CSV bytes and
validator failure, with writer/validator diagnostics captured. Final source digest frozen
before the corrected matrix:
`e064a19f27c8ca8171e2c9adda3151844eb8d369bf1e004659d75da5db06cef7`.
All 97 preregistered invariance keys per configuration are required in the cache.

### Attempt 3 result — final infrastructure verification

PASS. The exact frozen digest above completed one corrected synthetic/resource matrix,
then the actual `--full-match` CLI reused that validated cache without resource reruns.
The earlier attempt-2 final-decision wording is historical; this repaired cache/accounting
implementation is the final T08 evidence. No decoder, configuration, fixture expectation,
dependency or organizer code changed.

| Config | Strict contracts | Invariances | Feature/decode seconds | Peak RSS bytes | Eligibility |
|---|---:|---:|---:|---:|---|
| C0 | 23/23, zero mismatches | 97/97 | 0.543 / 0.725 | 235864064 | Eligible |
| C1 | 22/23, 2 mismatches (R02) | 97/97 | 0.620 / 0.933 | 230096896 | Rejected by R02 |
| C2 | 14/23, 129 mismatches | 97/97 | 0.584 / 0.801 | 238731264 | Rejected by frozen contracts |

All resources passed 120 s / 1 GiB. For every config, L01-live matched; L01-dead failed
80/80; L02-stoppage failed 60/60, with X expiry present and no D established. These remain
explicit coverage failures, not an overall robustness PASS. Selected C0 production checks
returned fixed **PASS**, including exact timeline, assessed/unassessed/dead mask invariants,
independent Result-array equality, identical output bytes and captured unchanged-validator
success. Production diagnostics/cache contents were not exposed. Asset-free tests: **91
PASS**; changed whitespace check PASS. Requested Sol Medium, effective model not exposed.

Decision: retain unchanged C0 as the simplest eligible reproducible engineering method;
C1/C2 are rejected ablations. No real-match accuracy/ranking claim. I03/I04 remain open,
T09 remains deferred, and T10 packaging is next. Coordinator owns final review/PLAN/commit.

### Coordinator checkpoint whitespace repair — preregistration

The staged diff check caught an extra blank line at the end of the newly added fixture
module (untracked files were absent from the earlier unstaged diff check). Removed only
that trailing blank line; model, fixtures and expectations are identical. Final checkpoint
source digest before verification: `b91715f70e2682e7cb10a9444010e7b2a9e4878cfbbebe599d4d95c6c22e68d3`. Run the same frozen matrix/resource
gates once for this exact source, then cached full-match CLI; no new candidate or method
comparison is introduced. Prior evidence remains historical.


Checkpoint result: **PASS**. All 91 tests pass; C0 23/23, C1 22/23 (2 mismatches), C2
14/23 (129 mismatches), with all 97 invariances/config passing. Synthetic feature/decode
seconds and peak RSS bytes: C0 0.542/0.776, 234602496; C1 0.546/0.749, 229015552;
C2 0.529/0.738, 235094016. All resource limits pass. The actual cached `--full-match` CLI
returns fixed PASS without rerunning resources. Stoppage witnesses remain the same explicit
failures; unchanged C0 remains the engineering choice. This is the source digest included
in the local checkpoint; no restricted diagnostics were exposed.
