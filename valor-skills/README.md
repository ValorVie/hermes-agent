# valor-skills — 本機客製 skill 的版本化來源

這個目錄存放 **本機（Valor / OpenClaw）客製過的 bundled skill 權威版本**，獨立於上游 `skills/` 樹之外，所以 `git rebase origin/main` 永遠不會與它衝突。

## 為什麼存在

部分上游 bundled skill（如 `kanban-orchestrator`）被本機加了大量機器專屬維運慣例（RockTeam 命名、任務監控流程、通知訂閱偏好等）。`sync_skills` 偵測到 user-modified 會跳過覆蓋，保護客製不被上游蓋掉，但 git 內的 `skills/...` 仍是上游原版 —— 客製只活在 runtime `~/.hermes/skills/`，沒有版本控管，誤刪即失。

本目錄是那份客製的 git 控管副本。

## 同步方向

**git (`valor-skills/`) 是權威來源，runtime (`~/.hermes/skills/`) 從它同步。**

- 升級流程中若對 runtime 版做了「無衝突自動合併」（吸收上游新段落），合併後要把 runtime 版**複製回對應的 `valor-skills/<name>/` 並 commit**，保持 git 版領先或同步。
- 詳細流程見 `platform-ops` SKILL 的 `references/hermes/update.md` 補差 #5「自動合併規則」。

## 目前收錄

| skill | 對應 runtime 路徑 | 客製內容摘要 |
|-------|-------------------|--------------|
| `kanban-orchestrator/` | `~/.hermes/skills/devops/kanban-orchestrator/` | RockTeam 命名慣例、任務 liveness 監控、通知訂閱偏好、cron `every 5m` 陷阱、main-gate 設計 + 上游 goal_mode 段落（已合併） |
