# Threads Viewer kanban first-change smoke note — 2026-05-06

## Situation

A kanban chain was started for `/home/openclaw/code/threads-viewer` after completing `workspace-scope-taxonomy`. The next OpenSpec change was `workspace-scope-billing-usage`.

## Useful task shape

First task was a research-only evidence pack:

- assignee: `research`
- workspace_kind: `dir`
- workspace_path: `/home/openclaw/code/threads-viewer`
- idempotency_key: `threads-viewer:workspace-scope-billing-usage:research-v1`
- title: `Research workspace-scope-billing-usage change readiness`
- explicit instruction: do not modify production code; do not commit
- required metadata keys:
  - `change_id`
  - `evidence_files`
  - `user_scoped_risks`
  - `required_tests`
  - `blockers`
  - `suggested_next`

## Verification pattern that worked

After `kanban_create`, verify with:

1. `kanban_show(task_id)`
   - expected events: `created`, then `claimed`, then `spawned`
   - expected run state: `runs[0].status == running`
   - expected task fields: `assignee`, `workspace_kind`, `workspace_path`, `current_run_id`
2. Check worker process if a `spawned` event has `pid`:
   - `ps -p <pid> -o pid,ppid,stat,etime,cmd`
   - expected command looked like: `hermes -p research --skills kanban-worker chat -q work kanban task <task_id>`
3. Inspect logs:
   - log path discovered at `~/.hermes/kanban/logs/<task_id>.log`
   - `read_file` or `hermes kanban log <task_id>` can show whether the worker has started tool calls.

## Pitfalls found

- `podman` was not available in this Hermes environment even though project docs mention Podman; Docker was active. For service checks, verify the live tool first instead of trusting project docs.
- `hermes-agent` skill was disabled in this environment; for Hermes kanban facts, use CLI help (`hermes kanban --help`) or inspect local docs when the skill cannot be loaded.
- `.rockspec-loop/state/current.yaml` did not exist for `threads-viewer`; do not assume RockSpec state exists before answering status questions.

## RockTeam chain used

For this user/project, the preferred kanban chain is:

`research → product → architect → coding → review`

Do not pre-create every card if later stages depend on the research metadata. Create the first card, wait for completion, then route based on `suggested_next` or blocker metadata.
