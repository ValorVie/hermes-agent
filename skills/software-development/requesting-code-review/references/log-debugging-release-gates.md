# Log debugging release gates

Use this when reviewing code that adds short-lived debug logs, especially security-sensitive logs around authentication, CAPTCHA, payments, webhooks, or customer data.

## Checks

- Verify every newly added helper file, test, and doc is staged before commit. `git diff` misses untracked files; use `git status --short` and `git diff --cached --stat`.
- If a controller hard-requires a new helper, a missing untracked helper can turn an observability change into a production fatal error. Treat this as a release blocker.
- For retention rules written as a glob such as `debug.log*`, count all matching files. Do not exclude lock files in tests unless the spec explicitly excludes them. Prefer lock names outside the glob, such as `.debug.lock` instead of `debug.log.lock`.
- For HTTP inaccessibility gates, do not accept `200 text/html` from a missing log URL as proof. It can be an app fallback page. Require one of:
  - a temporary real probe file in the target log directory returning 403/404 or otherwise inaccessible;
  - a concrete web-server deny rule check;
  - evidence that `DIR_LOGS` is outside the web root.
- Redaction tests should scan added diff lines and emitted log contents for secret/token/customer-data patterns, not just rely on manual inspection.

## Common blocker phrasing

- `request_changes`: new required helper is untracked or not included in staged diff.
- `request_changes`: lock file name matches the bounded retention glob and causes file count to exceed the stated limit.
- `request_changes`: HTTP probe does not prove an actual existing log file is protected.
