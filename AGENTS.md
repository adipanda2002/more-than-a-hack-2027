# Project working agreements

## Start and finish every task

- Read [PLAN.md](PLAN.md) at the start of every project task, including when resuming a chat. Check the current task, dependencies, open issues, decisions, and latest attempt before acting.
- The coordinator selects an existing task ID (or adds one), marks it `IN_PROGRESS` before implementation, and briefly names the outcome and worker model to the user. Delegated workers read this file and PLAN.md, but leave shared plan/status updates to the coordinator.
- After every attempt, the coordinator updates status and appends a dated attempt-log row with changes, checks/outcomes, unresolved issues, and next action. Workers return that evidence to the coordinator. Record failed or interrupted attempts too; never mark unverified work `DONE`.
- Update the plan's current/next task and review date before the final response. Keep the log concise and public-safe. Both the user and agent may edit the plan; preserve their changes.
- The plan records project state; organizer documentation remains authoritative for competition rules. Read the relevant rule/specification before changing behavior.

## Model routing for ChatGPT Plus ($20/month)

Use Standard speed. Default workers to GPT-6 Luna; reserve GPT-6.1 Sol workers for deeper reasoning. Model availability is subject to the account/client. The table below routes worker requests, not changes to the coordinator's active model.

The user wants to keep the main chat on GPT-6.1 Sol Light and have task models routed automatically (2026-10-26). Use model-routed subagents for substantive project tasks according to this table. The coordinator stays on the user's selected model, reviews worker results, updates the plan, and makes logical commits. The main model does not silently switch; a worker is a separate model invocation. No per-task delegation confirmation is needed within this project scope.

| Task | Recommended model | Reasoning |
|---|---|---|
| T00 plan maintenance, T01 Git setup, routine documentation | `gpt-6-luna` | Low |
| T02 scripted asset checks; T03 environment, dependencies, verification command | `gpt-6-luna` | Medium |
| T04 evaluation protocol and leakage review | `gpt-6.1-sol` | Medium |
| T05 loaders, aligned feature computation, focused tests against an agreed design | `gpt-6-luna` | Medium |
| T06 dead-ball model; T07 temporal possession design and initial implementation | `gpt-6.1-sol` | Medium |
| T08 fixed experiment runs, report assembly, straightforward fixes | `gpt-6-luna` | Medium |
| T08 ambiguous failure analysis or a substantive method decision | `gpt-6.1-sol` | Medium |
| T09 optional broadcast synchronization, only if activated in the plan | `gpt-6.1-sol` | Medium |
| T10 packaging and technical-document drafting | `gpt-6-luna` | Low |
| T10 one focused final correctness/reproducibility review | `gpt-6.1-sol` | Medium |

- Keep conversation, plan edits, Git operations, and tiny changes in the coordinator when delegation would add overhead. Never claim the main model was switched.
- For substantive work, spawn one worker with the table's explicit `model` and reasoning effort. In this session, use a fresh context (`fork_turns="none"`) when overriding the model; pass a concise task, allowed paths, acceptance criteria, and instructions to read AGENTS.md/PLAN.md and respect data restrictions. Do not copy the entire chat or restricted assets into its prompt.
- Permit at most one running worker. Workers must not spawn descendants, edit shared plan/status, commit, push, or publish. The coordinator owns integration and verifies relevant evidence without automatically rerunning expensive checks already demonstrated.
- Reuse a worker only for the same task/model; use a fresh worker when the required model changes. Return concise findings and file references, never restricted data/extracts. Record requested worker settings; record the actual effective model only when exposed, otherwise `not exposed`.
- If a requested model or delegation is unavailable, disclose that and continue on the current model for suitable scoped work. Do not silently escalate to Astra or repeatedly retry unavailable models. A new main chat should keep this project's instructions; no global configuration change is required by this policy.
- Avoid Fast, Max/Ultra effort, parallel fan-out, repeated broad reviews, and speculative experiments. Delegation uses the same Plus allowance and adds coordinator/worker overhead; it is not guaranteed to reduce total usage.
- After two unsuccessful attempts at the same issue, reassess the approach and summarize evidence before further retries. Prefer a bounded Sol diagnosis over repeating an expensive loop.
- Do not buy credits, use billed APIs, rent compute, or change global model settings without explicit user authorization. Subscription limits vary; API prices do not describe included Plus usage. Do not promise a fixed number of tasks.
- Read only relevant files, keep tool outputs small, cache expensive local computations, and rerun checks only when changes or unresolved concerns justify them.

Routing basis, checked 2026-10-26: [OpenAI subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents), [model guidance](https://learn.chatgpt.com/docs/model-selection), [available models](https://learn.chatgpt.com/docs/models), and [Plus usage/pricing](https://learn.chatgpt.com/docs/pricing?codex-pricing-plans=individual). Recheck if availability changes; do not browse these again for every routine task.

## Data and evaluation boundaries

- Follow [RULES.md](RULES.md), [FAQ.md](FAQ.md), and [SUBMISSION.md](SUBMISSION.md). No manual labels/corrections or frame-specific exceptions for this match. No external human-produced annotations about this match.
- The public five minutes are pipeline checks only: never train, tune thresholds, rank candidate methods, or select a checkpoint using them. Full-match ranking is private.
- Process restricted assets locally. Never send raw assets or extracts to hosted LLMs, including through tool output, screenshots, notebooks, or exceptions. Write code using public schemas; return only public-safe validation summaries such as pass/fail. Local execution alone does not make model inference local.
- Keep assets and restricted intermediate files under ignored `data/` paths; keep credentials and private links out of version control. Do not publish reconstructable tracking/video derivatives.
- Use the tactical timeline: submission frames `0..199318`, ATD `frame_id - 1`. Keep published half boundaries separate from inferred possession states. Missing ball does not imply dead ball.
- Preserve the official evaluator and validator. Validate the exact submission file and ensure deterministic regeneration from pinned dependencies. Add focused tests for substantive logic; documentation-only edits need link/diff checks, not a full model rerun.

## Repository workflow

- Reuse this checkout. `origin` is the team's fork; `upstream` is the organizer repository. Inspect Git status before edits and preserve unrelated changes.
- Use `codex/` for any new branch. The user authorized incremental local commits on 2026-10-26: commit verified, coherent changes at logical checkpoints without asking again. Pushing or publishing still requires a separate user instruction.
- Before each checkpoint, inspect the diff, run checks appropriate to the change, update PLAN.md, and stage explicit paths. Commit code with its relevant tests/docs and plan update; do not use `git add .` or include unrelated work, restricted data, or secrets.
- Use concise commit messages naming the behavior and task ID, such as `feat: infer dead-ball states (T06)`. A task can span several coherent commits. Record incomplete/failed attempts honestly in the plan; checkpoint partial work only when it stands alone and the commit explains its limits. Do not rewrite history or amend existing commits unless requested.
- Report each checkpoint's short hash, outcome, checks, and next action. Record a commit by its task/message in the committed plan; the following task can add its hash if useful, avoiding a self-referential hash/amend loop.
- End with the outcome, meaningful verification, limitations, and next task/model; also record them in PLAN.md.
