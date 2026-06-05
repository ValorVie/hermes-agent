# DOM 事件委派與過期狀態除錯案例

## 觸發情境

使用者回報瀏覽器腳本或前端互動「常常拿到錯的項目」，例如點某篇文章的分享／複製按鈕，卻複製到另一篇文章的連結。

## 已驗證的除錯路徑

1. 先找目前實作的狀態保存點：例如 `lastActivePostUrl`、全域 selected item、最近一次點擊項目。
2. 建立最小重現，至少包含：
   - A 項目可成功解析。
   - B 項目解析失敗或 DOM 結構不同。
   - 點 B 後執行 copy/action 不可沿用 A 的狀態。
3. 用真實或新版 DOM fixture 建立覆蓋測試，不只測人工簡化 HTML。
4. 對事件目標使用最近的項目容器定位，例如 `target.closest('[data-pressable-container="true"]')`。
5. 容器中若有多個候選連結，優先使用語意更強的候選，例如含 `<time>` 的 permalink，而不是第一個 `/post/`。
6. 在 menu/popover 注入時把當次解析出的 item URL 綁到按鈕閉包；不要在點擊自訂按鈕時再讀可變全域狀態。
7. 解析失敗時清空或拒絕執行；不要 fallback 到上一筆狀態或目前頁面 URL，避免靜默產生錯誤輸出。

## 常見根因

- 往上爬 DOM 過深，進入 feed/list 容器後 `querySelector` 拿到其他項目的第一個連結。
- popover/menu 是非同步插入，按鈕點擊時全域狀態已被其他互動覆寫。
- 解析失敗時沿用上一筆狀態，造成錯誤結果看似隨機。
- 貼文內含 media、quote、embedded link，單純取第一個 `/post/` 不是 permalink。

## 驗證訊號

- 測試能重現「本次解析失敗不可沿用上一筆」並在修復前失敗。
- 測試能在新版 DOM fixture 中逐一點多個 action button，確認每個結果對應該項目。
- 語法檢查與 diff whitespace 檢查通過。
