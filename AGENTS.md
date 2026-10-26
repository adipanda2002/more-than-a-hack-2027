# Project working agreements

## Start and finish every task

- Read [PLAN.md](PLAN.md) at the start of every project task, including when resuming a chat. Check the current task, dependencies, open issues, decisions, and latest attempt before acting.
- Select an existing task ID, or add one for new work. Mark it `IN_PROGRESS` before implementation and name the intended outcome briefly to the user.
- After every attempt, update the task status and append a dated attempt-log row with what changed, checks and outcomes, unresolved issues, and the next action. Record failed or interrupted attempts too; never mark unverified work `DONE`.
- Update the plan's current/next task and review date before the final response. Keep the log concise and public-safe. Both the user and agent may edit the plan; preserve their changes.
- The plan records project state; organizer documentation remains authoritative for competition rules. Read the relevant rule/specification before changing behavior.

## Model routing for ChatGPT Plus ($20/month)

Use Standard speed. Default to GPT-6 Luna; reserve GPT-6.1 Sol for work requiring deeper reasoning. These are recommended settings, not automatic model switches or guarantees of account availability.

GPT-6.1 Sol Light is suitable for coordination, questions, and scoped edits if the user prefers it. The same selected model also performs tool-driven work in this chat; there is no separate, automatically routed execution model. Recommend a picker change before substantive work when it would help quality or budget, without interrupting every minor subtask.

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

- Use the current model for a small task already in progress rather than launching another agent just to match this table. Never claim a model was switched when it was not.
- If a different model is appropriate, tell the user the recommended model/effort for the next task; they select it in the model picker. Record the actual model only when exposed, otherwise write `not exposed`.
- If a recommended model is unavailable, use an available lightweight equivalent or the current model and disclose the substitution. Do not silently escalate to Astra.
- Avoid Fast, Max/Ultra effort, repeated broad reviews, and speculative experiments. Use one agent unless the user explicitly requests delegation; this file does not authorize it.
- After two unsuccessful attempts at the same issue, reassess the approach and summarize evidence before further retries. Prefer a bounded Sol diagnosis over repeating an expensive loop.
- Do not buy credits, use billed APIs, rent compute, or change global model settings without explicit user authorization. Subscription limits vary; API prices do not describe included Plus usage. Do not promise a fixed number of tasks.
- Read only relevant files, keep tool outputs small, cache expensive local computations, and rerun checks only when changes or unresolved concerns justify them.

Routing basis, checked 2026-10-26: [OpenAI model guidance](https://learn.chatgpt.com/docs/model-selection), [available models](https://learn.chatgpt.com/docs/models), and [Plus usage/pricing](https://learn.chatgpt.com/docs/pricing?codex-pricing-plans=individual). Recheck if availability changes; do not browse these again for every routine task.

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
