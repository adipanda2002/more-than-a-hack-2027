# T06 prospective experiment record

## T06-E01 — 2026-10-26

- Hypothesis recorded before running: sustained coherent in-pitch displacement provides alive
  evidence; a visible stationary ball clearly outside supplies stoppage evidence. Confirming
  windows offline and including their first observation should avoid artificial restart delay.
  Finite same-half retention should survive brief missingness without inventing dead ball.
- Tree: T06 working tree based on T05 commit `bbd23aa`; source `possession/dead_ball.py`, tests
  `tests/test_dead_ball.py`; no RNG. Config: `Config()` (all values below). Fixture version:
  unchanged T04 `synthetic_cases()` plus independent T06 noise/expiry/boundary tests.
- Defaults chosen prospectively in physical units: 0.4 s motion confirmation, at least 0.5 m/s
  net movement and 0.2 m displacement, net/path ratio >=0.6 to reject coordinate jitter;
  45 m/s apparent ball-speed ceiling rejects isolated tracking jumps. Require 0.75 m beyond
  the pitch (boundary/calibration tolerance) and 0.6 s with bounding-box diagonal <=0.6 m
  for stationary outside evidence. Retain either supported state for at most 3 s after its
  latest confirmed evidence, a short occlusion budget rather than permanent inference.
- Evidence/split: artificial inputs only for behavior; supplied automatic features only for
  invariant/determinism smoke. No public GT, candidate quality score, labels or match inspection.
- Acceptance: all unchanged T04 cases pass when H/A expectations are projected to alive;
  focused uncertainty/noise/half-reset contracts and the full unit suite pass. Local smoke
  must deterministically return valid states/masks, unknown on unassessed frames, with no
  stored outputs or raw-data diagnostics. This does not constitute a full H/A/D model pass.
- Run ID: T06-E01 initial; feature smoke reuses T05 cache when valid.
- Final result: PASS after the implementation repair below. All 48 unit tests pass,
  including all eight unchanged T04 alive/dead projections and added noise, sparse-evidence,
  expiry and reset contracts. Fixture-contract preflight and sanitized local feature-consumer
  invariant/determinism smoke pass. No thresholds or T04 fixtures changed.
- Decision: retain this simplest initial evidence component for T07 integration. This is not
  full team-possession inference or real-match quality evidence; in-pitch and unavailable-ball
  stoppages remain a known coverage gap. Requested worker: GPT-6.1 Sol, Medium; effective model
  not exposed. No persistent inference outputs created.

### T06-E01 initial failure and repair intention

Initial full suite: FAIL (46 tests executed; existing tests pass). NumPy 2.4 treats IntFlag
operands as int64, so in-place OR into uint8 reason arrays raises a casting error before
inference. No behavior contracts or defaults were changed. Focused repair hypothesis:
convert flags to Python integers at array operations, preserving exact flag values and dtype;
rerun full suite and then local smoke only if the suite passes. This is an implementation
compatibility repair, not a method/configuration comparison.

### Final checks and follow-up

Commands: `.venv/bin/python -m unittest discover -s tests -q` (48 PASS),
`.venv/bin/python -m evaluation.behavioral_harness --check-contracts` (8 contracts PASS;
not a candidate H/A/D pass), `.venv/bin/python scripts/check_dead_ball.py` (PASS), and
`git diff --check` (PASS). The smoke was first run after the repaired suite passed, then rerun
following the final empty-input guard and added low-confidence tests; no feature recomputation
was requested. No public scorer or candidate quality scoring was run.

Before the initial run, the coordinator requested explicit consideration of in-pitch stoppages.
The chosen initial scope exposes confirmed in-pitch stationarity and tag context but leaves the
combination undecided: stationary observations plus automatic phase/player quiescence do not
observe the referee and may occur during live play. No threshold was changed in response to
match data or test outcomes. Next action: coordinator review, logical T06 checkpoint, then T07
team-possession design using these three-way states without treating unknown as D.
