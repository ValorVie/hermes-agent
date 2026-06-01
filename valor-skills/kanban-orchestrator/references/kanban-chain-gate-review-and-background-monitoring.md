# Kanban chain gate review and background monitoring

Use this when orchestrating a gated chain such as `research → product → architect → coding → review`, especially when the next stage would modify production code or data.

## Pattern: parent `done` is not enough

A worker's `done` status means the worker completed its own assignment. The orchestrator still owns the handoff gate.

Before creating the next child task:

1. Read the parent task with `kanban_show <task_id>`.
2. Inspect `runs[*].metadata`, especially artifact paths such as `requirement.md`, `design.md`, `plan.md`, test evidence, or commit hash.
3. Read the long-form artifact if the next child will implement, deploy, migrate, or review high-risk work.
4. Compare the artifact against upstream decisions and non-goals.
5. Only create the child task if the handoff is coherent and safe.

## If the handoff is flawed

Do not forward a flawed handoff to the next stage.

Use this sequence:

1. Add a comment on the flawed task explaining the exact gate blocker.
2. Create a corrective task for the upstream owner, with `parents=[flawed_task_id]`.
3. Include the artifact path, the specific conflicting lines or section, and the decision it violates.
4. Subscribe the active chat/thread to the corrective task.
5. After it completes, inspect the revised artifact before creating the next stage.

Example blocker:

- Architect migration plan says to delete legacy records.
- Product non-goal says legacy data cleanup is out of scope.
- Correct action: comment on architect task, create a new architect revision task, and only create coding after the revised artifact removes destructive deletion.

## Data migration gate checks

For migration or schema handoffs, inspect for these before creating a coding task:

- Does the plan delete, rewrite, or backfill legacy records?
- Is data deletion explicitly authorized by product / user decision?
- If legacy retention is a non-goal, does the plan use a non-destructive strategy such as nullable staging, quarantine, or follow-up data-rights work?
- Does runtime fail closed even if the database schema stays nullable for phase-one compatibility?
- Are temporary files or generated scratch files called out so coding does not accidentally commit them?

## Background monitor for long-running child tasks

If a coding or review worker may outlive the current chat context, create a small no-agent cron monitor instead of relying on memory. For this user's long Kanban chains, the monitor should do two jobs: status notification and automatic chain continuation. Do not wait for the user to ask "what stage are we at?" before creating the next valid child task.

Recommended shape:

1. Write a deterministic script under `~/.hermes/scripts/monitor_<workstream>.py`.
2. The script should:
   - read `~/.hermes/kanban.db` directly or call `hermes kanban show/list --json` via `subprocess.check_output`, not a shell pipe into Python;
   - track active tasks in the target workspace and print concise status transitions;
   - subscribe the active Discord/Telegram thread to every active or newly created task;
   - when a known parent changes to `done`, inspect latest run metadata and the referenced artifact path before creating a child;
   - create the next child only when there is no existing child and metadata contains a valid `suggested_next.assignee`;
   - use a stable idempotency key such as `<project>:auto-chain:<parent_id>:<assignee>`;
   - dispatch immediately after creating the child;
   - write monitor state under `~/.hermes/kanban-monitors/` so repeated cron runs do not spam;
   - if status is `blocked`, `crashed`, `gave_up`, or `timed_out`, write a terminal marker and print a concise alert instead of creating the next task.
3. Register it with cron, for example:

```bash
hermes cron create \
  --name "monitor coding t_xxxxxxxx" \
  --script monitor_t_xxxxxxxx.py \
  --no-agent \
  --schedule "every 10m" \
  --repeat 24
```

Exact CLI flags may differ by Hermes version; check `hermes cron create --help` when implementing.

## Pitfalls

- Do not wait for the user to ask before routing the next stage after a valid parent handoff; that creates avoidable idle time and defeats the orchestrator role.
- Do not pipe untrusted command output directly into an interpreter. Capture output inside a Python script with `subprocess.check_output` and `json.loads`.
- Do not create the entire downstream chain if the shape depends on parent artifacts.
- Do not treat notification subscription as inherited through `parents=[...]`; subscribe every programmatically created child task.
- Do not rely on a context compaction summary as the only monitor state; persist a marker file or use the Kanban task database.
