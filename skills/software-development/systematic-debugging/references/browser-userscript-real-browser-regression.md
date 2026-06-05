# Browser/userscript real-browser regression note

Use this when a bug only appears in a real browser surface: userscripts, browser extensions, clipboard APIs, permissions-policy, cross-origin frames, DOM event retargeting, or SPA menu reuse.

## Lesson

Unit tests with jsdom can validate pure DOM helpers, but they do not prove browser integration paths:
- `navigator.clipboard.readText()` can be blocked by Permissions Policy on the real site.
- A page may not call the API you hooked, producing a timeout despite passing synthetic unit tests.
- SPA menus may be reused; closures that capture an old DOM/menu URL can later copy the wrong item.
- Click targets may be SVGs, wrappers, counters, or sibling spans. Test at least one non-ideal hit target.

## Recommended sequence

1. Reproduce the user-visible path with Playwright or another real browser runner before claiming fixed.
2. Add a failing browser regression for the reported symptom.
3. Fix the smallest source of the bug.
4. Add edge-case browser checks for stale menu reuse and non-SVG/wrapper hit targets when DOM event targeting is part of the bug.
5. Keep unit tests for pure URL normalization and fallback behavior.
6. Verify with both suites plus syntax/format gates.

## Example commands

```bash
npm run test:unit
npm run test:browser
npm test
node --check path/to/userscript.user.js
git diff --check
```

## Stop condition

Do not report success until the real-browser regression passes and the test demonstrates the timeout/wrong-target path cannot recur in the normal user flow.
