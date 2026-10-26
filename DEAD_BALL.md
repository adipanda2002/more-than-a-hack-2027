# Dead-ball evidence component (T06)

`possession.dead_ball.infer(features, config=Config())` consumes the shared [T05
features](FEATURES.md). `infer_inputs(inputs)` adapts artificial T04 observations through the
same feature computation. It receives no expected labels or case names. Neither API assigns a
home/away team, writes a submission, reads public GT, or calls an evaluator.

The result has three aligned arrays:

| Field | Meaning |
|---|---|
| `state` | uint8 `State.UNKNOWN=0`, `ALIVE=1`, `DEAD=2`; internal evidence states, not submission labels |
| `assessed` | boolean graded AND positive published-half membership; unassessed states are unknown |
| `evidence` | uint8 OR of `Evidence` flags below; diagnostic reasons, never calibrated probabilities |

`MOTION=1` means a confirmed visible in-pitch movement window. `OUTSIDE_STATIONARY=2`
means a confirmed stationary window clearly outside the pitch. `RETAINED=4` means the
prior supported state was carried without fresh direct evidence. `SET_PIECE_CONTEXT=8`
and `NOISY_TAG_CONTEXT=16` retain automatic tag context and unknown/conflicting semantics.
`UNGRADED=32` marks unassessed frames (including absent half membership).
`STATIONARY_IN_PITCH=64` exposes confirmed stationarity for a later decoder; it does not
establish dead ball. Context flags may coexist with unknown and unassessed states.

For live evidence, a complete visible in-pitch window spans at least 0.4 seconds. Its endpoint
movement must meet both 0.2 m and 0.5 m/s times its duration; net/path ratio must be at least
0.6 and every apparent inter-frame speed at most 45 m/s. Coherence reduces coordinate-jitter
false motion and the ceiling rejects implausible isolated jumps. For dead evidence, the ball
must remain more than 0.75 m beyond one pitch edge for at least 0.6 seconds, with bounding-box
diagonal at most 0.6 m. These tolerances allow modest spatial noise without interpreting one
outside coordinate as a stoppage. Seconds are rounded up to whole frame steps; windows include
both endpoints. Confirmation marks the whole window, including its first observation, so a
restart is backdated to the first supported in-pitch observation rather than delayed by the
confirmation duration. Tags do not establish or shift boundaries, and team identities do not
enter this component.

Each supported state survives at most 3 seconds without fresh direct evidence, then becomes
unknown. This applies to missing ball, uncertain geometry and weak stationary observations.
Visible uncertain observations do not extend the expiry. No state or confirming window crosses
a published half boundary or an unassessed block. Published half membership and graded masks
are used independently of inferred game state: there is no kickoff-based exclusion, so graded
second-half pre-kickoff frames are still assessed. No frame constants from this match occur in
the inference code. A supported live state may persist over short stationary periods and brief
tracking failures; missingness alone never creates D.

Defaults were chosen prospectively from units and physical reasoning in [T06_EXPERIMENTS.md](T06_EXPERIMENTS.md). They are heuristics, not fitted parameters or verified referee-state
measurements. Moving a ball during dead time can resemble live play; calibration errors can
place a live ball outside; very slow or irregular live motion may remain unknown. In-pitch
stoppages and stoppages with an unavailable ball are largely missed by this initial method.
Stationarity plus a restart tag and apparent player quiescence could supply weak restart
context, but can also occur during live play and apparent track-slot speeds are unreliable.
This version deliberately leaves that combination undecided. It exposes stationarity and tag
bits plus the original features for T07 rather than declaring that combination D. A future
change requires a prospective hypothesis and independent synthetic tests.

Run asset-free contracts and the sanitized local smoke:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m evaluation.behavioral_harness --check-contracts
.venv/bin/python scripts/check_dead_ball.py
```

The smoke uses the existing feature cache when valid, runs inference twice, checks array/state/
mask/evidence invariants and exact equality, and prints only fixed pass/fail text. It stores no
prediction/cache/report files. The feature builder retains its own ignored, fingerprinted NPZ
cache. Do not print or publish production result arrays. Tests compare all eight unchanged T04
cases only after projecting expected H/A to alive; this is **partial dead-ball behavior evidence,
not a passing full H/A/D possession model**. T07 is not implemented. No real-match accuracy,
public-window candidate score, or hidden competition ranking has been measured.
