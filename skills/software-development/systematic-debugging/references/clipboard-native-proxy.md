# Clipboard Native-Action Proxy Notes

Use this reference when debugging browser userscripts, extensions, or UI automation where a custom button copies the wrong entity but the product's own copy/share action gets the right entity.

## Symptom pattern

- Custom action copies a stale or nearby item URL.
- If the user first clicks the product's native "Copy link" action, then the custom action works.
- This suggests the native product action refreshes internal target state that DOM scraping does not reliably reconstruct.

## Preferred fix shape

1. Stop widening DOM container heuristics when the native action is available.
2. Inject the custom action near the native action, but have it proxy through the native action.
3. Before clicking native action:
   - read and save the previous clipboard;
   - write a non-URL sentinel;
   - verify `navigator.clipboard.readText()` sees the sentinel.
4. Click the native action.
5. Poll clipboard until it changes away from sentinel.
6. Validate the copied value strictly:
   - expected host only;
   - expected path shape only;
   - reject external hosts with matching-looking paths.
7. Normalize the value and overwrite clipboard with the clean result.
8. On timeout, invalid output, or unreadable clipboard, restore previous clipboard and show failure.

## Race pitfalls

- A superseded older copy operation must not restore the clipboard over a newer operation.
- Add a monotonic sequence token.
- Check the token:
  - after every `await`;
  - before writing sentinel;
  - after reading sentinel;
  - before clicking native action;
  - before writing final clean URL;
  - before restoring clipboard in `catch`.
- If the token is stale, return without side effects.

## Regression tests to add

- Custom action uses native clipboard result even when DOM contains a wrong/stale URL.
- Native action writes asynchronously; custom action waits and does not clean stale clipboard.
- Menu is reused and the injected button updates its reference to the current native button.
- Media/tracking URL canonicalizes to base post URL.
- Native action writes non-post content; previous clipboard is restored.
- External host with post-shaped path is rejected.
- Sentinel is not observable; native action is not clicked.
- Native action never updates clipboard; previous clipboard is restored.
- Clipboard read API missing; fail closed.
- Rapid double-click / superseded operation cannot restore stale clipboard or leave a sentinel.
