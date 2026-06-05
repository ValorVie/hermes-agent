# Browser Network Isolation Review Notes

Use this reference when a code review touches server-side browser automation, Playwright, Browserless, Docker Compose network segmentation, SSRF defenses, or capture/scraping flows.

## Review checks

- Verify every browser context/page is protected before navigation or request-producing code can run. Prefer installing the routing guard immediately after context creation, not only inside a later helper.
- Treat `BrowserContext.route` / capture routing as a security boundary. If a refactor creates a new context path, the review must ask whether the guard is installed there too.
- Confirm production and test browser endpoints go through the intended restricted egress path. In Docker Compose, inspect both service networks and runtime listeners, not only environment variables.
- In `docker-compose.yml`, shell variables meant to expand inside the container command need Compose escaping such as `$${backend_ip}`. A single `$backend_ip` may be consumed during Compose interpolation and silently break the command.
- Verification should include a negative probe from the browser container to a blocked backend/control-plane target and a positive probe from the app container to the allowed control endpoint.
- Prefer stable HTML fixtures for integration tests. If an external page is necessary, use a page with predictable structure rather than `example.com` when assertions depend on DOM text/shape.

## Evidence to collect before accepting

- `docker compose config` passes.
- Targeted egress verification script passes.
- Integration capture/scrape tests pass from the same network context used by the service.
- Unit tests covering routing/billing/security helpers pass.
- A second review after fixes finds no Critical or Important items.