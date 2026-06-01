# Kanban main gate and no-agent monitoring

## Lesson captured

For Valor / OpenClaw's kanban RockTeam, the documented chain model is **not** fully automatic routing.

Correct flow:

```text
specialist task done
→ worker writes long-form artifact and metadata.suggested_next
→ main reads metadata + artifact
→ main decides: create next task / block for missing handoff / route upstream / close chain
```

The `suggested_next` field is advisory. It is a first-pass recommendation for main, not an instruction that scripts or specialist workers should execute automatically.

## Authoritative local docs

Use these docs before modifying kanban-chain behavior:

- `/home/openclaw/ai-home/docs/INDEX.md` — platform docs entrypoint.
- `/home/openclaw/ai-home/docs/guide/2026050609-02-hermes-kanban-使用指南.md`
  - Lines 271-283: main unified dispatch, passive mode.
  - Lines 420-433: specialist gives `suggested_next`; main decides.
- `/home/openclaw/ai-home/docs/superpowers/specs/2026-05-06-rockteam-kanban-migration-design.md`
  - Lines 38-42: non-goals include no cron auto-promotion and no main automatic routing.
  - Lines 185-189: main is the chain commander and sole decision point.
  - Lines 215-248: chain pattern returns to main between stages.

## Allowed monitor behavior

A no-agent cron monitor may:

- subscribe newly created tasks to the current Discord thread;
- report active / terminal status changes;
- detect missed fast completions between polling ticks;
- verify whether artifact paths exist and tell main when a handoff needs attention;
- remind that main needs to decide.

A no-agent cron monitor must **not**:

- infer the next task route;
- call `kanban_create` for the next specialist;
- dispatch children automatically from `suggested_next`;
- treat `review verdict=approve` with `suggested_next=main` as a stuck chain.

## Practical pitfall from 2026-05-07 session

A script was temporarily changed to auto-create follow-up tasks when it saw `suggested_next`. That contradicted the documented design. The correct correction is to make the script tracking-only and leave route decisions to main.

Another pitfall: Hermes cron schedule `5m` means one-shot "once in 5m". Use `every 5m` for recurring no-agent monitors and verify `repeat: forever` in `cronjob list`.

## Decision rule for future sessions

When a user asks "why did it stop?" after a kanban worker finishes:

1. Inspect `kanban_show(task_id)`.
2. If the worker is done and `suggested_next.assignee == main`, say it reached the main gate.
3. Read the artifact/report.
4. As main, decide and create the next task if the artifact supports it.
5. Do not modify monitors into automatic routers unless the user explicitly changes the design.
