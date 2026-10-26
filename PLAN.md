# Team reference plan — More Than a Hack 2027

Last reviewed: **2026-10-26 (Asia/Singapore)**. Maintained jointly by the user and agent.

## Current position

- **Current task:** none active; T00 sequential model-routed delegation is configured and its scoped worker review passed.
- **Next implementation task:** T03 — reproducible local environment and verification command. Worker route: **GPT-6 Luna, Medium, Standard speed**; main chat can remain on Sol Light.
- **Approach:** tactical-only, CPU-first; improve dead-ball detection and temporal possession structure before considering broadcast/video models.
- **Submission deadline:** November 17, 2026. Exact cutoff time/timezone is not stated in the repository; confirm from organizer communications.
- **Budget:** the user's $20/month ChatGPT Plus allowance; no purchased credits, paid APIs, or paid compute are authorized. Model routing lives in [AGENTS.md](AGENTS.md).

## How we maintain this plan

Read this file before every project task. Pick a task ID and check its dependencies, acceptance criteria, open issues, and prior attempts. Mark work `IN_PROGRESS` before implementation. After every attempt, including unsuccessful work, update status and append evidence plus a next action to the log. Update the current/next task before ending the turn. Both collaborators can add tasks or correct status.

Statuses: `TODO` = not attempted; `READY` = prerequisites met; `IN_PROGRESS` = active; `BLOCKED` = cannot proceed (record why); `DONE` = acceptance criteria verified; `DEFERRED` = deliberately outside the current path. Record partial progress in the log, not as completion. At most one task is active by default. Completed tasks may be reopened if new evidence invalidates them.

The task table and acceptance criteria describe planned work, not a claim that files or tests already exist. Historical checks below were run during this chat; a persistent verification script is part of T03.

## Incremental delivery and commits

The user authorized logical local commits on 2026-10-26. Implement one bounded outcome, verify it, update this plan, inspect/stage only its intended files, then commit. This authorization continues across project tasks; pushing/publication remains separate. Keep user changes and restricted assets out of unrelated commits. Do not rewrite existing history without a request.

Planned commit order (split further when a task has multiple independently useful changes):

1. `docs: establish incremental workflow and task plan (T00)` — current documentation checkpoint.
2. `chore: make local setup and verification reproducible (T03)`.
3. `test: define compliant evaluation and behavioral cases (T04)`.
4. `feat: build aligned tactical features (T05)`.
5. `feat: infer dead-ball states (T06)`.
6. `feat: infer temporal team possession (T07)`.
7. Focused fixes/experiment tooling selected under T04, with their evidence and limitations (T08).
8. Optional broadcast work only if activated (T09), then final reproducibility and submission documentation (T10).

Include relevant code, tests, documentation, and PLAN.md updates in the same logical checkpoint. Each final response reports the short commit hash and validation. Record a checkpoint by task/message in the committed plan; record its hash in a later update if useful rather than amending a commit to include its own hash. Do not label a failed or unverified attempt complete merely to make a checkpoint.

Keep the main chat on the user's selected GPT-6.1 Sol Light. Following the user's automatic-routing request on 2026-10-26, AGENTS.md now instructs the coordinator to delegate substantive tasks to explicitly selected worker models/efforts. Use at most one worker at a time; keep conversation and tiny changes in the coordinator. The coordinator reviews results, updates this plan, and commits. Workers receive concise fresh context and must not spawn other agents or commit. Both layers use the user's Plus allowance; delegation adds overhead and is not automatically cheaper. If delegation or a model is unavailable, disclose it and fall back to suitable work on the current model.

## Objective and fixed constraints

Produce a deterministic `frame,label` CSV with **199,319** data rows, labels `H/A/D/X`, on the tactical-video timeline. The private evaluation grades **158,857** frames and ranks by **spellF1**, with macroF1 as the first tie-break. The published full-match reference floor is **0.2433 spellF1**; we cannot measure our full-match score ourselves.

The competitive aim is qualification for the next round. Completion means a robust, compliant, reproducible submission with documented evidence and limitations; it cannot guarantee qualification against hidden labels and other teams. In particular, beating a public-window score cannot establish that we beat the full-match baseline.

Deliver the CSV, a public repository that regenerates it exactly, and a short technical document. Source of truth: [CHALLENGE.md](CHALLENGE.md), [DATA.md](DATA.md), [EVALUATION.md](EVALUATION.md), [SUBMISSION.md](SUBMISSION.md), [RULES.md](RULES.md), and [FAQ.md](FAQ.md). Preserve the official metric implementation.

Public ground truth is for pipeline correctness, never training or model/hyperparameter selection. No hand annotation/correction or external human-produced annotations about this match. Restricted assets/extracts stay out of cloud LLM context and public Git history. Local scripts may process them; only public-safe summaries belong in this plan or tool output.

## Task board

| ID | Task | Status | Dependencies | Completion evidence / acceptance criteria |
|---|---|---|---|---|
| T00 | Shared plan and agent/model instructions | DONE | None | Initial workflow checkpoint: `54edd78`. Sequential routing documented; read-only worker review requested Luna Low and returned PASS, including correct T03 route. Checkpoint: `docs: enable sequential model-routed workers (T00)`. Effective worker model not independently exposed. |
| T01 | Connect the existing checkout to the team fork | DONE | None | `origin` is `adipanda2002/more-than-a-hack-2027`; `upstream` is `metrica-sports/more-than-a-hack-2027`; local main tracks origin/main. |
| T02 | Verify supplied assets and reference pipeline | DONE | T01 | Nine expected assets present, nonempty, ignored and untracked; tactical alignment passes; all four regenerated baseline files identical to shipped files; public scorer matches documented results. Broadcast caveat tracked as I01. |
| T03 | Reproducible local environment and verification command | READY | T02 | Choose/document Python version, create .venv, pin minimal dependencies, and add a rerunnable check that reports pass/fail without printing restricted contents. Reference generation, official validation, and public scoring work in that environment. |
| T04 | Define a compliant evaluation/experiment protocol | TODO | T03 | Document permitted evidence and selection rules before candidate comparisons; implement meaningful synthetic behavioral cases; identify accessible, licensed other-match labels if needed, or record their absence. Freeze the public window's smoke-test role. |
| T05 | Tactical data and feature pipeline | TODO | T03 | Deterministic aligned arrays, team mapping, units, missing-value masks, half boundaries, and Smart Tagging semantics documented and checked. Cache restricted outputs only under ignored paths. No raw arrays printed. |
| T06 | Dead-ball inference | TODO | T04, T05 | Distinguish missing observations from stoppages using general motion/geometry/restart evidence. Handle noisy tags and unknown team values. Test behavior without match-specific hand labels. |
| T07 | Temporal possession inference | TODO | T04, T05, T06 | Transparent H/A/D state model with evidence for controlled turnovers and retention through loose balls/occlusion; emit a full-length valid CSV. Document uncertainty/X behavior under both metrics. |
| T08 | Robustness, experiments, and method selection | TODO | T04, T07 | Bounded experiments and ablations under the T04 protocol; deterministic runs and failure summaries. State limitations of evidence; no selection on public scores or private-GT-derived targets. |
| T09 | Optional broadcast investigation and integration | DEFERRED | T08, I01 | Activate only if the tactical approach has a clear evidence gap. Resolve timeline/count mismatch and validate synchronization before using broadcast features. Otherwise document why omitted. |
| T10 | Reproducible final submission package | TODO | T08 | Team-named CSV passes the unchanged validator; clean setup regenerates exactly the same file; pinned dependencies and commands documented; short technical document complete; data/secret exclusions checked. Include T09 only if activated. |

T04 and T05 may proceed independently after T03, but workers run sequentially to control usage. Route each substantive task through the model table in AGENTS.md: Sol for design/ambiguous decisions and Luna for scoped implementation and runs.

## Implementation checkpoints

### T03 — first task to execute

1. Check installed Python versions and select one supported by required dependencies. Python 3.12.1 currently runs the reference scorer successfully; no project virtual environment exists yet. Do not install a new interpreter unnecessarily.
2. Create `.venv` and pin the small dependency set. NumPy/pandas suffice for baseline and evaluation; add optional libraries only when a concrete task needs them.
3. Turn the previous ad hoc audit into a reusable, public-safe verification command. Keep generated baseline copies temporary or ignored; compare their hashes rather than exposing frame labels.
4. Record exact commands, environment, outcomes, and any dependency/version issues. A hash match demonstrates reference reproducibility, not improved possession quality.

### T04–T08 — modeling and validation

- Start with team/player proximity, motion, ball visibility, and automatic phase/restart evidence. Respect tag semantics: a defending team's tag is not direct evidence that it possesses the ball. Treat tags as noisy phases, not ground-truth possessions.
- Prototype a simple temporal state machine before adding more complex probabilistic or learned models. The testable goal is coherent intervals with justified turnover/stoppage boundaries, not just smoother per-frame guesses.
- Test general cases such as sustained control, transient deflections, missing ball inside possession, a genuine turnover after a gap, and a restart after dead ball. Do not encode observations at particular competition-match frames.
- Separate structural diagnostics from quality evidence. Possession counts/durations alone cannot establish correctness. Do not tune toward unpublished private-ground-truth statistics.
- Record each material experiment's hypothesis, code/config identifier, seed if applicable, permitted evidence, result, and decision. Repeated public-window scoring must not become a model-selection loop.
- Reuse local cached computations and keep comparisons bounded. Escalate complexity only when a specific failure justifies it.

### T10 — finish and submit

- Reproduce from a clean environment, then validate the exact final CSV and record its checksum locally.
- Document approach, assets used/omitted, any training data from other matches, possession rules, limitations, and execution command.
- Inspect Git exclusions and retained licensing; preserve organizer code attribution. Existing `.gitignore` excludes PDFs, so a technical document committed to the repo should be Markdown unless exclusions are deliberately adjusted.
- User supplies team name, confirms eligibility and the emailed submission form/cutoff. Submit CSV and technical document through the form alongside the public repository URL. Publishing, pushing, and form submission require the user's instruction when reached.

## Open issues and decisions

| ID | State | Issue / decision | Impact and next action |
|---|---|---|---|
| I01 | OPEN — optional path | Broadcast video reports one fewer frame than its tracking. Its last reported frame decodes; the final tracking index does not. | Does not block tactical work. Investigate container/decode/export alignment before T09; do not silently pad or shift it. No full-video decode audit has been performed. |
| I02 | OPEN — submission information | Team name/size, exact deadline timezone/hour, and emailed form URL are not recorded. | User can provide later; needed before T10 submission, not for local implementation. Teams need 3–5 members for later-stage eligibility. |
| D01 | ADOPTED | Tactical-only and CPU-first initial approach. | Use supplied tracking, tagging, and geometry; postpone broadcast synchronization and custom video models until justified. |
| D02 | UPDATED 2026-10-26 | Sol Light coordinator with sequential model-routed workers, Standard speed. | Follow AGENTS.md; one worker maximum, no nested agents, coordinator owns review/plan/commits. Requests select worker model/effort explicitly; the main model stays selected by the user. Both use the same Plus allowance. |
| D03 | ADOPTED | Public labels are a correctness example, not a tuning set. | Method decisions require the T04 protocol; preserve honest uncertainty about hidden-match performance. |
| D04 | ADOPTED | Restricted data stays local and out of model context. | Scripts may read assets, but return public-safe validation summaries; no footage, raw rows, screenshots, or reconstructable derivatives in chat/Git. |
| D05 | ADOPTED | Incremental, verified local commits are authorized. | Commit each coherent checkpoint with its plan update; report the hash. No push/publication or history rewrite is authorized by this decision. |
| D06 | ADOPTED | Competitive quality is the aim, not a promised selection result. | Address evaluation credibility in T04 and reproducibility in T10; be candid about the hidden full-match ranking. |

## Attempt log

Use Singapore-local dates. Add one row per meaningful attempt, including partial, failed, or blocked work. Include actual model only when exposed; a routing recommendation is not evidence of which model ran.

| Date | Task | Outcome | Evidence / changes | Next action | Actual model |
|---|---|---|---|---|---|
| 2026-10-26 | T01 | DONE | Existing checkout connected to team fork; organizers retained as upstream; main synchronized at verification. | Verify assets. | Not exposed |
| 2026-10-26 | T02 | DONE, with I01 | Expected files and Git exclusions checked. Tracking/homography structure and tactical frame alignment passed. Smart Tagging count/kickoff checks passed. Both videos opened and first frames decoded. Four regenerated baseline CSVs matched supplied files byte-for-byte; official public scores matched docs. Checks used temporary files, since removed. | T03; defer optional broadcast discrepancy. | Not exposed |
| 2026-10-26 | T00 | DONE | Added PLAN.md and AGENTS.md, with README links, task acceptance criteria, issue/decision log, and Plus-conscious model routing. Local links, task/routing coverage, and new/changed content whitespace checked. An initial whole-file whitespace check flagged pre-existing README formatting; corrected the check's scope and preserved that formatting. No modeling work started. | T03 using GPT-6 Luna, Medium, Standard speed. | Not exposed |
| 2026-10-26 | T00 | DONE | Added ongoing authorization for coherent verified local commits, commit order, explicit staging/check requirements, and model-picker clarification. Recorded qualification as an aim rather than a guarantee. Links, task/routing coverage, and changed-content whitespace pass. Checkpoint message: `docs: establish incremental workflow and task plan (T00)`; resulting hash reported in chat. | T03; use GPT-6 Luna Medium for budget efficiency, or the user's selected model for scoped work. | Not exposed |
| 2026-10-26 | T00 | DONE | Updated AGENTS.md and PLAN.md to route substantive tasks through one sequential worker while the main chat retains its selected model. Delegated a read-only documentation check with explicit `gpt-6-luna` / `low` and fresh context; it returned PASS and the correct T03 route. Local links and changed-content whitespace checked. Coordinator retains integration, plan updates, and commits. Checkpoint: `docs: enable sequential model-routed workers (T00)`. | T03 via a `gpt-6-luna` / `medium` worker; main chat can remain Sol Light. | Coordinator not exposed; worker requested Luna Low, effective model not exposed |

For future attempts, capture: **task ID; outcome; changed paths or local artifact locations; checks run/results; remaining issue; exact next action; actual model if known**. Keep historical entries accurate rather than rewriting failed attempts as successes.
