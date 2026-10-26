# Local setup and verification

Use Python 3.12 for the pinned project environment, tested here on 3.12.1. The official scorer and
reference baseline need only the small runtime in `requirements-local.txt`; video decoding,
notebooks, and `kloppy` remain optional and are not installed by this setup. The organizer's
unversioned `requirements.txt` remains available for the documented Python 3.8+ scorer support.

From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-local.txt
.venv/bin/python scripts/verify_setup.py
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`. Point
`MTAH_DATA_DIR` at the extracted data bundle when it is outside `./data`; `games.DATA_DIR` and
all existing loaders honor that setting.

The verifier checks that the tactical video, tracking metadata and data, homography, and Smart
Tagging files exist, are ignored and untracked when inside the checkout, and have the expected
public structure and frame alignment. An external `MTAH_DATA_DIR` does not need Git exclusions. It
checks optional broadcast files only for presence. It does not decode either video; the tactical
video is required to be present, but no decoder is needed for the baseline or evaluation. The
known one-frame broadcast tracking/video discrepancy does not affect this tactical-only check.

It then writes the four reference baselines to a temporary directory under ignored `data/`,
compares each with its supplied baseline hash, runs the unchanged official validator and public
scorer, and checks their published public-window scores. Child output is captured, and the command
prints only pass/fail summaries. Temporary submissions and reports are removed on exit. The public
five minutes are used only for this pipeline check; do not use these scores to select or tune a
method. The official validator and scorer remain unchanged.

## Asset-free behavioral checks

The team [evaluation protocol](EVALUATION_PROTOCOL.md) freezes the public window's smoke-test
role and defines independent synthetic cases for future possession models. These checks need no
match files or public ground truth:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m evaluation.behavioral_harness --check-contracts
```

The second command checks fixture structure; no candidate model is evaluated. Run the initial
T07 adapter with `--predictor possession.temporal:predict` in place of `--check-contracts`.
It passes all eight full behavioral contracts; synthetic correctness does not
establish real-match accuracy. Restricted model outputs and caches belong under ignored `data/`
paths; avoid printing asset records or extracts.

For aligned tracking, motion, geometry, and Smart Tagging features, see [FEATURES.md](FEATURES.md)
and run `.venv/bin/python scripts/build_features.py`. The command reports only a sanitized
build/cache status; arrays stay in the ignored local feature cache.

The [dead-ball evidence component](DEAD_BALL.md) provides alive/dead/unknown state and reason
masks used by the temporal decoder. Run `.venv/bin/python scripts/check_dead_ball.py`
for a sanitized local feature-consumer/invariant/determinism smoke. It creates no prediction
outputs or quality scores.

For the frozen T08 synthetic robustness and bounded resource checks, run
`.venv/bin/python scripts/run_robustness.py`. It is asset-free by default. The explicit
`.venv/bin/python scripts/run_robustness.py --full-match` option reuses a valid local report
and resource cache before running the selected C0 format/repeatability gate. Results remain
under ignored `data/` paths and do not score against possession labels.

For full H/A/D/X inference, see [TEMPORAL.md](TEMPORAL.md). Run
`.venv/bin/python scripts/generate_submission.py` to create the ignored local
`data/predictions/t07.csv`, then `.venv/bin/python scripts/check_temporal.py` to verify
independent decodes, identical CSV bytes and unchanged official format validation.
Both commands suppress private diagnostics and do not evaluate quality against public labels.

For the team-named release package, see [RELEASE.md](RELEASE.md). The final command rebuilds
features without cache and writes the team CSV, technical report copy, and private local manifest
under ignored `data/predictions/release/`.
