# Private non-fork mirror workflow

Use when the goal is to replace a public fork with a private repository that preserves upstream Git history but is no longer marked as a GitHub fork.

## Sequence

1. Preserve local work before destructive remote operations:
   ```bash
   mkdir -p /path/to/backups/repo-$(date +%Y%m%d-%H%M%S)
   git bundle create /path/to/backups/repo.bundle --all
   git format-patch -1 HEAD --stdout > /path/to/backups/0001.patch
   git diff origin/main..HEAD > /path/to/backups/local.diff
   git status --short --branch > /path/to/backups/status.txt
   ```
2. Create an empty private repo under a temporary name if the final name is occupied by an existing fork:
   ```bash
   gh repo create OWNER/REPO-private --private --description "Private mirror of UPSTREAM/REPO" --disable-wiki
   gh repo view OWNER/REPO-private --json nameWithOwner,visibility,isFork,isEmpty,url
   ```
3. Mirror upstream history into the empty private repo:
   ```bash
   tmpdir="$(mktemp -d)"
   git clone --mirror https://github.com/UPSTREAM/REPO.git "$tmpdir/repo.git"
   cd "$tmpdir/repo.git"
   git push --mirror https://github.com/OWNER/REPO-private.git
   ```
4. If GitHub rejects hidden pull-request refs (`refs/pull/*`) during `git push --mirror`, delete those refs from the bare mirror and retry:
   ```bash
   git for-each-ref --format='%(refname)' refs/pull | while read -r ref; do
     git update-ref -d "$ref"
   done
   git push --mirror https://github.com/OWNER/REPO-private.git
   ```
5. If upstream uses Git LFS, use bare clone plus LFS transfer:
   ```bash
   git clone --bare https://github.com/UPSTREAM/REPO.git "$tmpdir/repo.git"
   cd "$tmpdir/repo.git"
   git lfs fetch --all https://github.com/UPSTREAM/REPO.git
   git push --mirror https://github.com/OWNER/REPO-private.git
   git lfs push --all https://github.com/OWNER/REPO-private.git
   ```
6. Repoint the local working repo and apply or push local commits:
   ```bash
   git remote set-url origin https://github.com/OWNER/REPO-private.git
   git remote add upstream https://github.com/UPSTREAM/REPO.git 2>/dev/null || git remote set-url upstream https://github.com/UPSTREAM/REPO.git
   git fetch origin --prune
   git branch --set-upstream-to=origin/main main
   git push origin main
   ```
7. Only after verifying the private repo is complete and the user explicitly requested deletion, delete the old fork:
   ```bash
   gh repo delete OWNER/REPO --yes
   ```
8. Rename the private repo to the final name if needed:
   ```bash
   gh api -X PATCH repos/OWNER/REPO-private -f name=REPO
   git remote set-url origin https://github.com/OWNER/REPO.git
   git fetch origin --prune
   git branch --set-upstream-to=origin/main main
   ```

## Verification checklist

```bash
gh repo view OWNER/REPO --json nameWithOwner,visibility,isFork,defaultBranchRef,url
git ls-remote origin refs/heads/main
git status --short --branch
git remote -v
git log --oneline -1
```

Expected final properties:

- `visibility` is `PRIVATE`.
- `isFork` is `false`.
- `origin/main` points to the commit containing local changes.
- `upstream` still points to the original public repository.
- Worktree is clean.

## Pitfalls

- `git push --mirror` includes `refs/pull/*` from GitHub sources. GitHub rejects those hidden refs in the target repository. Delete them from the temporary bare mirror, not from the source repository.
- Do not delete the old fork until the private mirror, branches/tags, local change commit, and remotes are verified.
- `gh repo edit` cannot rename repositories in some CLI versions; `gh api -X PATCH repos/OWNER/OLD -f name=NEW` works directly.
- A final-name repo must be empty before mirror push. If the old fork owns that name, mirror into a temporary private repo, then delete old fork and rename.