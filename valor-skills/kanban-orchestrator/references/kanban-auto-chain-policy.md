# Kanban auto-chain policy — user-corrected operating rule

## Learning captured

In a RockTeam Kanban session, the user corrected an over-strict reading of "main gate" / "do not auto-dispatch":

- "Do not auto-dispatch" means: do not proactively start a Kanban chain when the user has not explicitly asked for Kanban / full-chain execution.
- Once the user explicitly asks for Kanban, RockTeam chain, complete chain, or automatic dispatch, the root task is authorized and the chain may auto-advance inside that scope.
- Specialist workers still should not create the next task themselves. Auto-advance belongs to main-owned automation such as a watcher/monitor script, not to individual specialists.

## Correct policy

Use this split:

| Phase | Human/main role | Watcher role | Specialist role |
|---|---|---|---|
| Before chain exists | Decide whether this request is explicitly Kanban / full-chain | Do nothing | Not involved |
| Root task creation | Create root task and mark/record `auto_chain=true` or equivalent policy | Start tracking only authorized chain | First assignee works |
| In-chain handoff | Define allowed roles and policy boundaries | Deterministically create next task from valid metadata | Complete own task with artifact + `suggested_next` |
| Exception | Decide product/safety ambiguity | Pause and notify | Block or report missing context |
| Review approve | Report final result | Treat as terminal; do not create more tasks | Review completes with `verdict=approve` |

## Guardrails for watcher auto-advance

A watcher may create a child task only when all conditions hold:

1. The task belongs to an explicitly authorized auto-chain root.
2. Parent is `done`.
3. Parent has no existing child, or the idempotency key resolves to the same child.
4. Metadata has a valid `suggested_next.assignee` in the allowed role list.
5. Required long-form artifact paths exist and are non-empty.
6. For review tasks:
   - `verdict=approve` is terminal; notify completion, create no child.
   - `verdict=request_changes` requires valid `route_decision` mapped to a role.
7. `blocked`, `crashed`, `gave_up`, and `timed_out` are notification-only in v1; do not auto-retry.

## Anti-pattern corrected

Do not write or preserve instructions like:

> Cron/script must not become an automatic router.

That statement is too broad. Replace it with:

> Cron/script must not start or expand unauthorized Kanban work. For explicitly authorized auto-chain roots, a watcher may perform deterministic in-chain handoff using metadata and structural artifact checks.

## Where to formalize in repo docs

For this user's ai-home platform docs, prefer opening an OpenSpec change before changing runtime rules. The canonical change created from the correction was:

`/home/openclaw/ai-home/openspec/changes/kanban-watch-autochain-architecture/`

Key files:

- `proposal.md` — product intent and non-goals
- `design.md` — architecture and watcher boundary
- `tasks.md` — follow-up implementation checklist
- `specs/kanban-watch/spec.md` — normative requirements
