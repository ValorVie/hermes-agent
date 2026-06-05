# Private repo Windows clone handoff

Use after creating or migrating a private GitHub repo when the user needs a Windows operator workflow, especially for Python GUI/tools that will be cloned and run from source.

## What to include

1. Current repo identity
   - private repo URL
   - upstream URL, if any
   - whether the repo is a GitHub fork or a non-fork mirror
   - expected local `origin` / `upstream` remotes
2. Access setup
   - `gh auth login` / `gh auth status`
   - fallback clone URL or SSH note
3. Clone commands
   ```powershell
   cd D:\Projects
   gh repo clone OWNER/REPO
   cd REPO
   git remote -v
   git status --short --branch
   git log --oneline -3
   ```
4. Add upstream, when applicable
   ```powershell
   git remote add upstream https://github.com/UPSTREAM/REPO.git
   git fetch upstream --tags
   ```
   If it may already exist, show `git remote set-url upstream ...`.
5. Runtime setup
   - required OS and toolchain
   - Python version and virtual environment commands if Python
   - dependency install command
   - if `pyproject.toml` / `uv.lock` exists or the user asks for uv, document `uv python install`, `uv sync --frozen`, and `uv run --frozen ...` instead of pip/venv commands
6. Launch workflow
   - exact commands to start the app
   - any admin/UAC requirements
   - runtime preconditions, such as required companion app/window state
7. Data and generated files
   - list local data/log/cache files
   - warn not to commit personal runtime data unless intentionally needed
8. Update workflow
   ```powershell
   git checkout main
   git pull --ff-only origin main
   git fetch upstream --tags
   git merge upstream/main
   # or: git rebase upstream/main
   git push origin main
   ```
9. Verification and troubleshooting
   - minimal test command
   - expected commit marker if a specific local patch matters
   - common auth, dependency, permission, and runtime-window failures
10. Commit the handoff doc
   - run `git diff --check`
   - run at least the relevant smoke/unit test when available
   - commit and push the documentation change

## Pitfalls

- Do not assume Windows users already have `upstream`; a fresh clone only has `origin`.
- If the repo was converted from a public fork to a private non-fork mirror, explicitly say the final repo is private and `isFork=false` so future operators do not re-clone the old fork model.
- For Python GUI tools, document both source execution and optional executable packaging. Make packaging optional when source execution is enough.
- For uv-based Python projects, include the project metadata files (`pyproject.toml`, `uv.lock`) and use `uv run --frozen` for launch/tests after `uv sync --frozen`; use an optional dependency group (for example `--extra build`) for packaging-only tools.
- Mention generated local data (`config.json`, logs, captures, build outputs) before telling users to commit, so they do not accidentally stage personal runtime files.
