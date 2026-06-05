# valor-skills — 已淘汰（客製改為 in-tree）

> **2026-06-05 起本目錄停用。** 本機客製的 bundled skill 不再放這裡，改為**直接客製上游 `skills/` 樹並 commit 進 `valor-feature` 分支**。

## 為什麼改

舊作法（valor-skills/）把客製放在上游 `skills/` 樹之外，目標是「`git rebase` 永不衝突」。但這個目標其實是錯的：

- **永不衝突 = git 永遠不會告訴你上游對這個 skill 改了什麼**，每次升級還是得手動 diff `valor-skills/` vs `skills/` 才知道要不要合併，沒有省掉判斷工，只是把訊號藏起來。
- runtime 會被 `sync_skills` 標為 user-modified 並跳過，導致上游更新沉默累積、長期漂移（實測累積到結構性損壞）。
- 版本化也不完整（如本目錄的 `kanban-orchestrator` 只存了 SKILL.md、沒存它的 5 個 references）。

## 新作法（in-tree 客製）

把客製直接改進 `skills/<path>/<name>/`（SKILL.md + references/），commit 進 `valor-feature`。好處：

- **rebase 時 git 自己就是合併引擎**：上游改同一行才衝突（= 你要的判斷時機，行級精確），改不同段落自動合併、自動吸收上游內容。
- **`sync_skills` 不再跳過**：runtime == bundled 後不再是 user-modified，上游更新自動經 sync 傳到 runtime。
- 客製是對上游的**純新增 diff**，未來 rebase 多數自動合併。

硬約束：**永遠用 `git rebase origin/main`、絕不用 `hermes update`**（後者 `git reset --hard` 會毀掉 valor-feature commit）。

## 純本機 skill（上游沒有的）

若未來有完全自創、上游不存在的 skill，沒有合併對象，可放回本目錄或其他明確標記的位置。目前沒有這類 skill，本目錄保留此說明作為指引。

詳見 `platform-ops` SKILL 的 `references/hermes/update.md`「user-modified skill 紀律」章節。
