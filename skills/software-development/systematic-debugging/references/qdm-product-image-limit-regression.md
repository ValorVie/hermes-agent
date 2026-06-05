# QDM 商品頁圖片限制／自動停用回歸調查筆記

## 適用場景

使用者要求檢查 QDM / OpenCart 類舊系統中「商品無法儲存」、「商品被自動停用」、「圖片張數限制突然生效」等回歸問題。

## 本次已驗證的調查路徑

1. 先確認 Git 狀態與遠端差異：
   - `git status --short --branch`
   - `git rev-list --left-right --count HEAD...origin/master`
   - 若本地落後且使用者同意，用 `git rebase origin/master`；有未提交檔案時先 `git stash push -u`，rebase 後再 `git stash pop`。
2. 用近期 commit 縮小範圍：
   - `git log --oneline --since='YYYY-MM-DD' -- <product files>`
   - `git log -S'<symbol-or-message>' -- <files>`
   - `git log -G"status\s*=\s*'0'|forceDisableProduct|content_max_image" -- <files>`
3. 對疑似行為做 blame：
   - `git blame -L <start>,<end> -- admin/controller/catalog/product.php`
   - `git blame -L <start>,<end> -- admin/model/catalog/product.php`
4. 確認語法：
   - `php -l admin/controller/catalog/product.php`
   - `php -l admin/model/catalog/product.php`

## 關鍵發現範例

- PR #2247 `fix/admin-product-image-upload-limit` 讓商品頁真正套用 `content_max_image`。
- `content_max_image=10` 來自 `storeinfo`，登入時進 session：`admin/controller/common/login.php`。
- 商品圖超量時，controller 會呼叫 `forceDisableProduct()`，model 直接執行 `UPDATE product SET status = '0'`。
- 4/30 的 toast 變更只讓儲存錯誤更可見，不是停用根因。

## 重要除錯教訓

- 舊 PHP controller 的 validator 可能有資料庫副作用；不要把 `validateForm()` 預設視為純檢查。
- `update_prod()` 這類 AJAX + LZString 壓縮路徑可能在 `validateForm()` 時仍未解壓，檢查要追到解壓後的第二段邏輯。
- 「以前沒限制」可能不是設定不存在，而是原有方案限制長期未被前端或後端正確執行。
- 對客訴回報要分開：已確認、推論、待確認、建議處理。避免把產品決策包成技術事實。
