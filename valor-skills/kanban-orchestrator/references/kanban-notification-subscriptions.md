# Kanban notification subscriptions

Session-derived note from 2026-05-06.

## Problem

Kanban tasks created through gateway slash commands can be auto-subscribed to the source chat, but tasks created programmatically with `kanban_create` or `hermes kanban create --json` do not inherit that chat subscription. If the user asks whether they will be notified, verify the subscription table instead of assuming.

## Verification commands

```bash
hermes kanban notify-list
hermes kanban notify-list <task_id>
hermes kanban notify-subscribe --help
```

Expected empty state:

```text
(no subscriptions)
```

## Subscribe a task

```bash
hermes kanban notify-subscribe <task_id> \
  --platform discord \
  --chat-id <channel_or_thread_id> \
  [--thread-id <thread_id>] \
  [--user-id <user_id>]
```

Then verify:

```bash
hermes kanban notify-list <task_id>
```

Example verified in session:

```bash
hermes kanban notify-subscribe t_7cc874a9 --platform discord --chat-id 1496039961072238714
hermes kanban notify-list t_7cc874a9
# t_7cc874a9  discord:1496039961072238714  (since event 0)
```

## Delivery semantics

Gateway notifier polls `kanban_notify_subs` and sends terminal events for:

- `completed`
- `blocked`
- `gave_up`
- `crashed`
- `timed_out`

After terminal delivery, the gateway advances the cursor and usually removes the subscription.

## Built-in progress / verbose limits

Current Hermes Kanban has no Discord-facing `verbose` mode for notification subscriptions. Treat the built-in notifier as terminal-event delivery only.

Observed command behavior:

- `hermes kanban notify-subscribe` requires explicit `--platform` and `--chat-id`; in Discord threads also pass `--thread-id` when available. Do not rely on ambient Discord session env to infer them.
- `hermes kanban tail <task_id>` prints that task's event stream locally, including payloads, but does not send Discord messages.
- `hermes kanban watch` can live-watch board events locally and can filter kinds, but is not a notification subscription.
- `hermes kanban daemon --verbose` only affects standalone dispatcher logging and is not a gateway/Discord progress mode.
- Gateway notifier terminal kinds are `completed`, `blocked`, `gave_up`, `crashed`, and `timed_out`; process events like `created`, `claimed`, `spawned`, and `running` are not forwarded by `notify-subscribe`.

When the user wants visible progress transitions such as `ready → running → done`, use a no-agent monitor that reads `kanban.db`, records a small snapshot file, and posts only state changes to the origin chat. Keep it idempotent and workspace-scoped.

## Late-subscribe recovery

If the user asks to subscribe after a task may already have advanced, check task status before promising notifications:

```bash
hermes kanban show <task_id>
hermes kanban runs <task_id> --json
hermes kanban notify-list <task_id>
```

If the task is already terminal (`blocked`, `done`, `gave_up`, `crashed`, `timed_out`), immediately report the terminal summary / reason to the user. Do not make the user discover it by running `list`.

If you still need to subscribe for future events on the same task without replaying the old terminal event, subscribe with the correct Discord thread coordinates and seed the cursor to the current last event:

```bash
TASK=<task_id>
CHAT=<discord_parent_or_thread_channel_id>
THREAD=<discord_thread_id>  # omit or set empty when not in a thread
MAX_EVENT=$(sqlite3 /home/openclaw/.hermes/kanban.db \
  "select coalesce(max(id),0) from task_events where task_id='$TASK';")
hermes kanban notify-subscribe "$TASK" --platform discord --chat-id "$CHAT" --thread-id "$THREAD"
sqlite3 /home/openclaw/.hermes/kanban.db \
  "update kanban_notify_subs set last_event_id=$MAX_EVENT where task_id='$TASK' and platform='discord' and chat_id='$CHAT' and thread_id='$THREAD';"
hermes kanban notify-list "$TASK"
```

Use the same pattern after unblocking if you want future `completed` / re-`blocked` events to reach the current thread.

## Discord target notes

- If subscribing to a Discord thread and you know the parent channel plus thread id, pass `--chat-id <parent_channel_id> --thread-id <thread_id>`.
- Hermes `send_message list` exposes known Discord targets. Thread-style entries may show a topic id that can be used as the Discord destination id when no direct source metadata is otherwise available.
- Do not restart `hermes-gateway.service` just to make subscriptions work unless the user explicitly approves a gateway restart.

## Operational pitfalls

For a chain such as `research → product → architect → coding → review`, subscriptions are per task. A child task does not automatically inherit the parent task subscription when created programmatically. Subscribe each newly created task if the user expects notifications for every stage.

`notify-subscribe` is a terminal-event forwarder, not a progress tracker. It only sends `completed` / `blocked` / `gave_up` / `crashed` / `timed_out`; it does not replay `created` / `claimed` / `spawned`, and it does not send periodic "still running" messages.

For Discord, a delivered Kanban notification is just a normal bot message in the target thread/channel. It does not automatically `@mention` the requester, and current gateway notifier code stores `user_id` but does not include it in the message body. If the user expects push-style pings or visible progress transitions, add a separate no-agent cron watcher that prints state changes to the origin chat, or send an explicit message from the orchestrator.

## Lightweight auto-tracking monitor pattern

When the user says every Kanban task in a project must be tracked, do not rely on manual discipline alone. Create a no-agent cron monitor that scans active tasks for the project workspace and subscribes any missing rows to the current chat/thread.

If the user is specifically frustrated by progress opacity, extend the monitor beyond subscription repair: keep a compact JSON snapshot of `{task_id: status/current_run_id/assignee}` and send a short message only when a task changes state or a new active task appears. This fills the native notifier gap without spending model tokens.

Minimal pattern:

```python
#!/usr/bin/env python3
import sqlite3
import subprocess
from pathlib import Path

DB_PATH = Path.home() / ".hermes" / "kanban.db"
WORKSPACE = "/path/to/project"
PLATFORM = "discord"
CHAT_ID = "<channel_or_thread_id>"
THREAD_ID = "<thread_id>"  # empty string if not in a thread
ACTIVE_STATUSES = ("todo", "ready", "running")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
placeholders = ",".join("?" for _ in ACTIVE_STATUSES)
tasks = conn.execute(
    f"""
    select id, title, status, assignee
    from tasks
    where workspace_path = ?
      and status in ({placeholders})
    order by created_at asc
    """,
    (WORKSPACE, *ACTIVE_STATUSES),
).fetchall()

for task in tasks:
    exists = conn.execute(
        """
        select 1
        from kanban_notify_subs
        where task_id = ? and platform = ? and chat_id = ? and thread_id = ?
        limit 1
        """,
        (task["id"], PLATFORM, CHAT_ID, THREAD_ID),
    ).fetchone()
    if exists:
        continue
    subprocess.run(
        [
            "hermes", "kanban", "notify-subscribe", task["id"],
            "--platform", PLATFORM,
            "--chat-id", CHAT_ID,
            "--thread-id", THREAD_ID,
        ],
        cwd=WORKSPACE,
        text=True,
        capture_output=True,
        check=True,
    )
    print(f"Subscribed {task['id']} {task['status']}/{task['assignee']}: {task['title']}")
```

Install with a no-agent cron so it does not burn model tokens:

```bash
hermes cron create \
  --name "<project> kanban auto-tracking" \
  --schedule "every 5m" \
  --script <script_name>.py \
  --no-agent \
  --deliver origin
```

Prefer workspace-scoped monitors over a global monitor unless the user explicitly wants all project notifications in the same channel. This avoids flooding an unrelated Discord thread.
