# Polyamal — technical report

Registered team: **polyamal** (five members). The emailed submission form has not yet been received.

## Method

The submission uses the unchanged C0 temporal possession method in `possession/temporal.py` and `possession/dead_ball.py`. It uses automatic tactical player and ball tracking, aligned to the published tactical frame timeline, plus game metadata for team and slot mapping. Positions are converted to metres before applying geometry rules. Fresh control requires a nearest-team distance at most 2.0 m, an opponent distance margin of at least 0.5 m, and a constant-team run spanning at least 0.4 s (ceil(seconds × FPS) + 1 frames). Observed consecutive in-pitch ball speed must be at most 12 m/s when finite; stationary close control is eligible and player–ball co-motion is not required; confirmation is backdated to the beginning of the supported run. The method retains supported ownership for a finite three seconds through short uncertainty, then abstains as X. Published half and graded-frame boundaries reset state. H and A mean the inferred team, D means the component has established dead-ball evidence, and X means unknown or unassessed.

The dead-ball proxy establishes D from a visible ball more than 0.75 m beyond any pitch edge, observed throughout a 0.6 s window whose bounding-box diagonal is at most 0.6 m. It retains evidence for at most 3 s. Alive evidence requires a complete in-pitch 0.4 s window, net displacement at least max(0.2 m, 0.5 m/s × window duration), displacement/path-length ratio at least 0.6, and step speed at most 45 m/s. Windows contain ceil(seconds × FPS) + 1 frames and evidence is backdated across confirmed windows. Missing ball and in-pitch stillness do not establish D. The rules are physical heuristics, not measurements of player control or referee decisions. Close proximity can assign possession without a controlled touch; loose balls, challenges, partial visibility, and long gaps can produce incorrect ownership or X. In-pitch and missing-ball stoppages are a known gap.

## Assets and data

Used: the supplied tactical automatic tracking, its metadata, and Smart Tagging loaded for diagnostic/context features only. Smart Tagging is not treated as possession labels or boundary truth. Homography, tactical/broadcast video, broadcast tracking, and synchronization were not used. No external data was acquired. No labelled datasets, training, learned weights, manual labels, manual corrections, or frame-specific exceptions were used. Public labels were not used for training, tuning, candidate selection, or checkpoint selection.

LLMs assisted with coding and documentation only. Restricted match assets and extracts were not sent to hosted LLMs. All asset processing and inference are local.

## Evaluation and limitations

The unchanged C0 was retained after a frozen, bounded comparison of three configurations on synthetic contracts and engineering checks. C0 satisfied the 23 synthetic semantic contracts; all configurations had 97 tested invariances. The T08 record also contains two deliberately failed limitation witnesses: the available observations cannot distinguish live stationary possession from an in-pitch stoppage, and missing-ball stoppages are not inferred as D. These checks validate specified synthetic behavior and reproducibility only. No real-match accuracy, public-window candidate score, full-match ranking, qualification, or competition outcome is claimed. The private full-match ground truth was not accessed.

Ranking uses spellF1: one-to-one temporal-IoU matching of H/A spells, averaged over thresholds 0.3–0.7 in steps of 0.1. macroF1 is the first tie-break. Ground-truth X frames are excluded. Predicted X on graded frames is a miss for macroF1; temporal metrics forward-fill within each half and back-fill its leading X run. Thus abstention can extend the previous predicted possession in scoring. The unchanged organizer metric implementation remains authoritative.

## Reproduction

Use Python 3.12 and install the pinned local requirements as described in `SETUP.md`. With the authorized data bundle extracted under `data/` (or `MTAH_DATA_DIR` set to its location), run:

```bash
.venv/bin/python scripts/package_submission.py --team polyamal --no-cache
```

This regenerates `data/predictions/release/polyamal.csv`, validates that exact CSV using the unchanged organizer validator, copies this report to `data/predictions/release/polyamal.md`, and writes a local reproducibility manifest. Generated files stay under ignored `data/`. The team name must match the registration form. Submission deadline: November 17, 2026; the repository does not specify the cutoff time or timezone. The emailed submission form is still pending; the registered name is confirmed as polyamal.

This work uses the competition's supplied automatic tracking, metadata, and Smart Tagging assets under their participant terms; it does not redistribute those assets.

Repository code and documentation retain the MIT License, Copyright (c) 2026-2027 Metrica Sports; the full notice and permission text are preserved in `LICENSE`. This license does not cover the restricted match assets.
