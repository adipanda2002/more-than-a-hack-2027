# Team evaluation and experiment protocol (T04)

This protocol governs T05–T08 development. The organizer's [rules](RULES.md),
[challenge definitions](CHALLENGE.md), [metric implementation](evaluation/possession_metrics.py),
[evaluation guide](EVALUATION.md), [FAQ](FAQ.md), and [submission contract](SUBMISSION.md)
remain authoritative. This file adds conservative team selection rules; it does not replace them.

## Evidence and permitted decisions

| Evidence | Permitted use | Cannot establish |
|---|---|---|
| Public five minutes and published reference scores | A fixed correctness smoke check: timeline, schema, label mapping, reference reproduction, scorer wiring | Hyperparameters, thresholds, method ranking, checkpoint selection, training targets, or generalization |
| Independently authored artificial cases below | Test explicit behavioral contracts, reject regressions, debug general logic | Real-match accuracy, realistic boundary uncertainty, or competition ranking |
| Supplied automatic inputs without ground truth | Deterministic feature/alignment checks, missingness/motion diagnostics, algorithmic inference | Accuracy, possession count/duration targets, or proof of control |
| Accessible, suitably licensed labels from different matches, if acquired | Development selection and a separately frozen generalization test under the gate below | Performance on the supplied match or a guaranteed hidden ranking |

Freeze the public window as correctness smoke only. Do not choose a smoothing window, threshold,
architecture, feature set, method, seed, checkpoint, stopping point, or winner using its labels or
scores. Do not inspect candidate disagreements against those labels to improve possession logic.
Run the established reference smoke via `scripts/verify_setup.py` after relevant pipeline changes;
do not run a candidate leaderboard as a selection loop. A wiring defect may be repaired using
public schema/alignment specifications, with a recorded synthetic regression; a low public score
is not a defect diagnosis. Repeated scoring, confidence intervals, or a larger bootstrap cannot
turn this window into permitted selection evidence.

No hand labels, manual corrections, external human game annotations, frame-specific exceptions,
or human-selected pseudo-label corrections for the supplied match, for any purpose. Never use
private ground truth or statistics derived from it, including possession counts/duration targets.
Published baseline scores describe reference behavior; they do not make hidden statistics
available. Our own counts/durations can diagnose flicker or bugs, but optimizing those numbers to
look plausible is not quality validation.

## Independent real-match validation gate

**No accessible, licensed other-match possession benchmark has currently been validated or
installed for this project.** This is a known generalization risk. It does not block generic
feature work, synthetic regression testing, or a reproducible rule-based submission. It does
prevent claims that a candidate improves real-match quality or beats the published full-match
floor. A synthetic pass alone cannot rank candidates for the hidden match.

Before T08, permit one bounded acquisition investigation: inspect at most two publicly accessible
other-match sources, spend at most one project work session, and record URL/version, access terms,
redistribution permissions, organizer access, match identities, annotation origin/coverage, team
mapping, timestamps, units, missingness, and possession/dead-ball semantics. A tracking or event
dataset is not automatically possession ground truth; verify the labels and definitions. Reject
the supplied match, leaked/corrected data from it, inaccessible sources, incompatible licensing,
or labels that cannot support the intended claims. Do not purchase data or label the supplied
match. If neither source passes, record “none validated” and continue the transparent synthetic
and engineering path. No dataset search or acquisition is represented as completed by T04.

If other-match labels pass that gate, freeze a manifest and split by **whole match** before
selection: development matches for bounded choices, disjoint held-out match(es) for one final
assessment. Keep adjacent windows, alternate exports, clips, mirrored copies and the same match
in one split. Fix label conversion, boundary tolerances and metrics before opening held-out
labels. Do not fill missing annotations with assumed labels or treat event coverage as exhaustive.
With only one labelled match, keep it developmental; do not claim an independent match holdout.
Record any mismatch with the challenge's controlled-possession definition. A failed held-out
assessment is reported; reopening it for tuning consumes that holdout and requires a new match
for an independent claim. Neither split includes the public five minutes.

## Synthetic behavioral contract

Run without competition assets, videos, public GT, or extra dependencies:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m evaluation.behavioral_harness --check-contracts
```

[behavioral_cases.py](evaluation/behavioral_cases.py) invents metre-scale trajectories at 10 fps
on a 100 × 60 m pitch. These are not samples, extracts, annotations or parameters from the supplied
match. Player slots identify observations only, not stable player identities. Expectations are
separate half-open intervals `[start, stop)` authored from the scenario intent, not calculated by
nearest-player logic, tags, or a candidate predictor.

The small adapter contract for T05–T07 is:

| Object | Fields / meaning |
|---|---|
| `Inputs` | Immutable `observations`, positive `fps`, `pitch_m=(length,width)` |
| `Observation` | Consecutive zero-based `frame`; chronological `half` 1/2; `ball_xy` in metres or `None`; tuple of `Player`; tuple of automatic `Phase` priors |
| `Player` | `team` H/A or `None` for unknown; observed `xy` metres. Missing players are absent, not positioned at zero |
| `Phase` | Automatic `code`, optional H/A `team`; unsupported codes/teams are weak or absent evidence |
| Predictor | `predict(inputs: Inputs) -> iterable[str]`, one H/A/D/X per input frame, deterministic for a fixed configuration |

Future adapters may derive distances, speeds and masks from these observations. Production
schemas may be richer; preserve units, missingness and half semantics when adapting. The
predictor receives no case name, intended controller, expected intervals, control/restart oracle,
or fixture index. Never add such answer-bearing fields as production features. Frame is an index
for alignment and time differences, not a way to memorize these boundaries. Fixture construction
helpers and test stubs are not production predictors. Use fresh per-call model state; reset any
possession memory on a half change, even for batch/offline inference.

| Artificial case | Explicit expected intervals | Behavior under test |
|---|---|---|
| Sustained control | H `[0,80)` | Stable co-motion stays one possession |
| Transient opponent deflection | H `[0,80)` | One opponent proximity/contact frame does not confer control |
| Missing ball inside possession | H `[0,80)` | Missing ball `[30,50)` does not imply D |
| Loose ball | H `[0,80)` | No opponent control: retain previous team through `[30,45)` |
| Controlled reception after gap | H `[0,50)`, A `[50,100)` | Retain H during gap; sustained opponent co-motion establishes turnover at first reception |
| Visible dead ball and restart | H `[0,30)`, D `[30,60)`, A `[60,100)` | Visible stationary ball outside pitch differs from occlusion; restart phase intentionally overlaps live play |
| Half reset | H `[0,40)`, A `[40,90)` | Clear away control begins the second half; do not delay it with stale first-half team memory |
| Noisy phase prior | H `[0,80)` | An away defending tag and unknown phase do not override observed home control |

These exact boundaries are prospective engineering contracts for idealized inputs, not a universal
operational definition of control. The model may use future observations to confirm and backdate
reception. In real tracking a brief nearby opponent may actually control the ball, an out-of-pitch
coordinate may be noise, and the referee's restart instant is unobserved. A phase can be false or
misaligned. These fixtures deliberately do not resolve those ambiguities or imply that arbitrary
geometry uniquely determines possession. Their duration/offset constants are fixture construction
choices, never calibrated production thresholds.

The exact synthetic boundaries are not official scoring tolerances. Offline lookahead or
backdating is permitted; no causal-only inference or half-head abstention policy is required.
The harness compares raw labels strictly: it does not forward-fill X, so a
model emitting X instead of retained H fails this retention contract even where official spellF1
would fill it. Under the official metric, X misses on macroF1 and is filled within each half for
spellF1; X across a turnover can incorrectly extend the prior possession. D always means actual
stoppage; neither missing ball nor low confidence alone justifies it. Smart Tagging phases are
noisy priors, never possession labels.

[behavioral_harness.py](evaluation/behavioral_harness.py) checks full expectation coverage, input
indices, output lengths, label alphabet, and every frame including both sides of transitions.
Malformed outputs raise an interface error; valid wrong outcomes return failed case results. An
adapter can be evaluated later with:

```bash
.venv/bin/python -m evaluation.behavioral_harness --predictor your_module:predict
```

`your_module:predict` is an example import target, not an implemented candidate. The committed
tests use constant stubs, independently written test timelines and deliberate wrong predictions
(including D for missing ball, a one-frame false turnover and stale half state) to test the
harness. The initial [T07 decoder](TEMPORAL.md) passes all eight full behavioral contracts; this
is synthetic behavior evidence, not measured real-match quality. `--check-contracts`
validates fixture structure only. Keep that statement distinct from future model results.

## Prospective bounded experiments and decision gates

1. **T05 engineering gate:** one deterministic aligned-feature implementation. Check synthetic
   units/masks/team mapping and published timeline invariants; cache local computations once.
   No possession-quality claims from feature distributions. Proceed when alignment checks pass.
2. **T06/T07 behavior gate:** one initial transparent state model with a frozen configuration
   chosen from physical reasoning and explicit contracts. Run all synthetic cases. Permit at
   most two focused repair attempts per failure, each with a hypothesis; then reassess before
   another run. Fix general behavior, never case IDs, frame constants or answer-bearing markers.
   A pass permits integration, not a claim of improved real-match scores.
3. **T08 comparison gate:** preregister at most three total configurations (initial model plus
   two single-factor alternatives) and their rationale before running comparisons. Do not sweep
   thresholds. Use synthetic regressions as contract gates and deterministic runtime/resource
   checks as engineering evidence. If independent development labels exist, rank by spellF1,
   with macroF1 as tie-break, and disclose sample/definition limits; assess the frozen choice once
   on the disjoint holdout. Without them, retain the simplest passing, reproducible method by an
   explicit engineering decision; do not label it the empirically best possession model. Any
   expanded budget needs a new recorded hypothesis and protocol decision, not silent retries.
4. **T10 release gate:** regenerate deterministically with pinned dependencies, compare exact
   output bytes/hashes across clean runs, and run the unchanged validator on the exact final
   submission. Validate all 199,319 tactical frames `0..199318`, H/A/D/X, ATD `frame_id - 1`.
   Use published half boundaries for segmentation/reset; do not infer them from predicted state.
   Published pre-kickoff semantics remain separate from possession inference. File validity and
   reproducibility establish submission readiness, not hidden ranking quality.

Before every material experiment, append a record with: experiment/task ID; date; hypothesis;
code commit/tree identifier; configuration identifier and values; seed (or deterministic/no RNG);
fixture version; permitted evidence source and split; metric/contract and acceptance rule;
run/cache identifier; result/pass/fail; limitations; decision and next action. Fill the hypothesis,
configuration and acceptance rule **before** the run, and result/decision after it. Log failed or
interrupted runs. Record any fixture change and its general justification; weakening a contract
to fit a model is not an improvement. Public-safe decisions belong in PLAN.md; a compact synthetic
experiment table may be versioned. Do not log restricted per-frame evidence there.

## Local processing and safe outputs

Restricted assets and intermediates (arrays, caches, predictions, clips, detailed failures and
reports) stay under ignored `data/` paths, for example `data/cache/` and `data/experiments/`.
Use manifests with code/config, dependency versions and source hashes for deterministic cache
invalidation. A cache hit is not new validation. Keep credentials/private URLs out of logs/Git;
verify ignore/tracking status before writing artifacts. Synthetic fixtures/code and sanitized
aggregate pass/fail summaries are safe to review and commit.

Never send raw restricted assets or extracts to hosted/cloud LLMs via prompts, tool output,
screenshots, notebook cells, exceptions or attachments. Local execution of a cloud-backed model
does not make inference local. Catch/sanitize errors from restricted-data processing before
returning summaries; do not print records to debug. Do not publish reconstructable tracking/video
derivatives. Final submission handling follows the organizer's approved channel; keep local
candidate copies ignored. Preserve the official evaluator/validator and distinguish their schema
checks from this separate synthetic harness.
