# T07 prospective experiment record

## T07-E01 — 2026-10-26

- Hypothesis (before running): a team that stays uniquely close to a visible in-pitch ball
  supplies a transparent control proxy. Requiring sustained evidence suppresses brief opponent
  contacts. Backdating confirmed runs to their first observation avoids artificial turnover
  delay. Finite ownership memory bridges loose balls and brief missingness; explicit T06 dead
  evidence resets ownership, and published half/ungraded boundaries reset all memory.
- Tree: T07 working tree based on T06 checkpoint; code `possession/temporal.py`,
  `possession/submission.py`, `scripts/generate_submission.py`, `scripts/check_temporal.py`.
  Requested worker GPT-6.1 Sol Medium; effective model not exposed. No RNG.
- Frozen initial defaults: nearest team distance <=2 m; opposing nearest distance at least
  0.5 m farther; both teams observed; visible in-pitch ball; apparent ball speed <=12 m/s
  when speed is available. Require a continuous run spanning 0.4 s (both endpoints included).
  Carry confirmed ownership at most 3 s after fresh confirmed support. T06 defaults unchanged.
  These are physical heuristics, not tuned match thresholds. Tags supply no labels.
- Evidence/split: unchanged eight T04 cases plus independent synthetic persistence, ambiguity,
  noise, reset and dead/restart tests. Production features used only for invariants,
  determinism and format smoke. No public labels, evaluator or candidate quality score.
- Acceptance: all eight full H/A/D/X contracts, focused synthetic tests and existing unit suite
  pass; safe output-path tests pass; full-match inference is deterministic, unassessed labels
  are X, explicit dead states are D, CSV follows the published frame schema. Generate twice,
  compare bytes locally, and validate the exact output using the unchanged organizer validator
  with stdout/stderr captured. Expose only fixed production pass/fail summaries.
- Run ID: T07-E01 initial, reusing the existing feature cache. Results pending.
- I04 decision: in-pitch stationarity, missing ball, player quiescence and noisy phase tags do
  not establish a referee stoppage. This initial decoder does not promote them to D. Coverage
  remains incomplete; passing artificial contracts is not evidence of real-match quality.

### Initial run failure and focused repair intention

Initial synthetic suite: 69 tests, one FAIL and one ERROR. Seven unchanged T04 contracts
pass; visible restart is delayed one frame because the speed ceiling consumes displacement
from an outside dead-ball coordinate to the first in-pitch observation. Repair hypothesis:
apply the control speed gate only to adjacent observed in-pitch, same-half, assessed pairs;
a cross-boundary displacement is not a live-control velocity. No numerical default changes.
Independent empty-player observations also expose a pre-existing shared-feature zero-slot
`nanmin` reduction. Guard that reduction when no finite distances exist; retain NaN geometry
and zero counts. This feature implementation fix invalidates the fingerprint and justifies
one automatic feature-cache rebuild. No T04 contracts or expected boundaries change.

### Repair result and independent regressions

The focused repair passed the suite: first 69 tests, then 70 after adding an independent
outside-to-inside speed-discontinuity regression for both teams. The zero-slot test also
checks shared feature shapes, NaN nearest distances and zero team counts. All eight unchanged
T04 full H/A/D/X contracts pass with zero mismatches. Added tests cover finite retention,
short-contact rejection in both directions, exact backdated turnovers, FPS duration units,
missing opponents, ties, fast/outside ball rejection, noisy geometry/tags, symmetry,
determinism, half/ungraded resets and dead-state clearing. No defaults were changed.

### Final outcome and checks

PASS after the one focused repair above. Final suite: 74 tests PASS. All eight unchanged
full behavioral contracts PASS with zero mismatches. Added output tests verify outside/raw
asset/cache destinations, traversal, symlink/dangling links, directories, ignored/tracked
checks, exact synthetic CSV bytes, rejected timeline preservation, atomic-failure cleanup,
validator capture, rejection before asset loading and exception/library-output sanitization.

Commands run:

- `.venv/bin/python -m unittest discover -s tests -q`: 74 PASS.
- `.venv/bin/python -m evaluation.behavioral_harness --predictor possession.temporal:predict`:
  all eight full synthetic contracts PASS.
- `.venv/bin/python scripts/check_temporal.py`: fixed PASS for full-match invariants, two
  independent decodes, equal CSV bytes and unchanged official validation of both files.
  One feature-cache rebuild followed the shared empty-reduction fix; subsequent generation
  reused the fingerprinted cache. Only fixed summaries were exposed.
- `.venv/bin/python scripts/generate_submission.py`: fixed PASS, including validation of the
  exact generated `data/predictions/t07.csv`. It remains ignored/untracked locally; the smoke's
  second temporary output was removed. No restricted arrays, counts or hashes were exposed.
- `git diff --check`: PASS. Organizer validator/evaluator and all T04 fixtures unchanged.

Decision: retain this initial transparent, deterministic implementation as the T07 engineering
checkpoint. No real-match quality, public score or hidden ranking improvement is claimed.
I04 and the proximity/control ambiguity remain open. There were no threshold/configuration
comparisons, public GT reads or evaluator runs. T08 comparisons/ablation decisions remain a
separate task under the frozen evaluation protocol. Coordinator owns PLAN, review and commit.
