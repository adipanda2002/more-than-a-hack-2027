# Temporal team possession (T07)

`possession.temporal.infer(features)` combines shared [features](FEATURES.md) with the
unchanged [T06 evidence model](DEAD_BALL.md). It returns aligned `labels`, `control`, `assessed`
and `dead_state` arrays. `predict(inputs)` is the observations-only T04 behavioral-harness
adapter; it never receives case identities or expected labels. No match-specific frame
constants, public GT, candidate scoring, learned parameters or RNG enter this decoder.

Within each contiguous graded positive-half block, a fresh control candidate requires a
visible in-pitch ball, at least one observed player from each team and finite per-team nearest
ball distances. The nearest team must be within 2 m and at least 0.5 m closer than the opponent.
Where available on adjacent assessed in-pitch observations in the same half, ball speed must
be <=12 m/s. Cross-boundary jumps are not treated as live ball velocity. These physical
heuristics are control proxies: proximity does not prove a touch, and no player identity,
co-motion or multi-player support confirmation is required in this initial model.

A candidate must persist continuously for at least 0.4 s, including both endpoints of the
window. Confirmed runs are backdated to their first observation, including at half starts
and restarts. A confirmed opposing run turns possession over at that first observation;
a one-frame opponent deflection does not. Ambiguous/tied proximity, loose balls, missing ball
and missing opponents do not establish a new owner. The previous owner survives at most
3 s after its latest confirmed control evidence, then the output becomes X. There is no
future-owner fill across an unsupported gap. Every published half change and ungraded block
clears ownership and prevents confirmation windows from crossing it.

T06 DEAD emits D and clears ownership, including its finite retained dead evidence. Confirmed
motion in T06 can establish a restart and backdate the end of D; subsequent team control
still needs its own confirmation. T06 UNKNOWN never becomes D. T06 ALIVE alone does not
supply a team. Conversely, sustained stationary near-ball geometry can supply a team proxy
while T06 remains UNKNOWN: that is an ownership hypothesis, not a claim that the referee has
resumed play. `dead_state` preserves this distinction for diagnostics.

Smart Tagging phases do not supply labels or alter transition boundaries. I04 remains open:
in-pitch and unavailable-ball stoppages are largely missed, and a player standing near a
stationary dead ball may receive H/A. Stationarity, player quiescence and restart tags can
also occur during live play, so this version does not force that weak combination into D.
Moving a ball during dead time can also fool T06. Requiring both teams observed can increase
abstention; track loss and loose passes longer than 3 s can erase ownership. Close opponents,
fast controlled play or sustained incidental proximity can miss or invent turnovers. These
limits are not measured real-match error rates; no independent labelled benchmark is available.

X is emitted outside assessed blocks or when ownership and dead state are unsupported.
On graded frames X misses under macroF1. The official spellF1 fills X with the last label
within each half; abstaining across a turnover can therefore extend an old possession. The
strict synthetic harness checks the emitted H/A/D/X directly, before that fill. Passing it
establishes the specified artificial behaviors, not improved hidden ranking quality.

Frozen defaults, initial failures, repair rationale and verification evidence are in
[T07_EXPERIMENTS.md](T07_EXPERIMENTS.md). The shared feature correction for empty synthetic
player sets preserves NaN distances/zero counts rather than reducing an empty slot axis;
its fingerprint change causes one cache rebuild, with no production schema change.

## Reproduce and verify locally

Use the existing environment and pinned [requirements](requirements-local.txt), as described
in [SETUP.md](SETUP.md). From the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m evaluation.behavioral_harness --predictor possession.temporal:predict
.venv/bin/python scripts/generate_submission.py
.venv/bin/python scripts/check_temporal.py
```

The generator writes `data/predictions/t07.csv` with all 199,319 tactical frames and the exact
`frame,label` header, then invokes the unchanged organizer validator. The smoke independently
decodes twice, writes two files, compares bytes locally, validates both and deletes the
second temporary file. The primary ignored CSV remains for local review/submission handling.
These commands never read public labels or run an evaluator. Each production command emits
fixed pass/fail text only; validator stdout/stderr (including derived counts/durations) and
other local diagnostics are captured, never relayed to hosted LLM context.

`--data-dir` selects an asset root; `--output data/predictions/name.csv` selects a local CSV.
Outputs must be beneath this checkout's dedicated `data/predictions/` tree, ignored and
untracked. Traversal, symlink components (including dangling links), non-CSV files and
directories are rejected. Raw assets, feature caches and organizer result paths cannot be
overwritten by this tool. A regular existing ignored output can be atomically replaced.
Temporary files are created in its parent and removed on failure. Destination and timeline
checks precede writing; the destination is checked again before replacement. The official
CSV validator runs after replacement; a validation failure returns nonzero and leaves the
generated file in place. The checks protect ordinary local use; concurrent hostile changes
to filesystem permissions/paths are outside this single-user workflow.

No outputs, tracking derivatives, private diagnostics or data counts should be committed or
published. The initial CSV is an engineering checkpoint; T08 method comparisons and T10 final
team-named release packaging remain separate tasks.
