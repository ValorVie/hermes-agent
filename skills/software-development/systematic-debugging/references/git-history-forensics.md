# Git History Forensics for Bug Timelines

Use this when a bug report includes claims like "this used to work" or "it only broke recently," especially when the current fix/restoration commit may obscure an older regression.

## Pattern

1. Identify the exact variable, guard, route, or side-effect that controls the behavior.
2. Check the current implementation and the parent before the suspected fix:
   ```bash
   git show <fix-merge>^1:path/to/file | grep -n '<symbol>'
   git blame -L <start>,<end> <fix-merge>^1 -- path/to/file
   ```
3. Search content history, not just commit messages:
   ```bash
   git log --date=iso-strict --format='%h%x09%ad%x09%an <%ae>%x09%s' -S'<literal>' -- path/to/file
   git log --date=iso-strict --format='%h%x09%ad%x09%an <%ae>%x09%s' -G'<regex>' -- path/to/file
   ```
4. If the expected working version is not found on `master`, search all visible refs:
   ```bash
   git for-each-ref --format='%(refname)' refs/heads refs/remotes refs/tags \
     | while read ref; do git grep -n '<symbol>' "$ref" -- path/to/file 2>/dev/null; done
   ```
5. Separate conclusions:
   - "Visible Git history proves..."
   - "Not found in visible Git history..."
   - "Could still exist in production backup, pre-import code, or uncommitted hotfix..."

## Pitfall

A restoration commit can look like the start of behavior. In one QDM investigation, a 2026 commit reconnected `content_max_image`, but `git blame` showed the front-end guard existed since the 2022 initial import while its limit variable was `-1`, disabling the guard. The correct report separated:

- earliest visible disabled state,
- later AJAX save-path change,
- recent auto-disable side effect.
