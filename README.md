# 淘寶雙 11 歷史價格分析器（MVP）

繁體中文個人購物價格分析工具。**分開處理「手動確認的同 SKU 實付價」與「第三方商品級歷史報價」**，避免把先漲後降、不同規格、滿減門檻混為一談。支援桌面與手機瀏覽器。

## 已完成

- 新增淘寶／天貓商品（同商品不同 SKU 分開管理），解析常見商品網址 ID。
- 手動記錄售價、折價、運費、最終實付價；標示試算價，記錄來源。
- CSV／文字歷史價格匯入、完整 JSON 備份與還原、圖表與 30/90/180 天篩選。
- 同規格**已記錄實付價**比較：先前低點、30/90 天中位數、樣本信心提醒、雙 11 暖身期抬價警示。
- 讀取 `data/provider_history.json` 之第三方**商品級參考價**，獨立圖線及明細；不把它當成交價或相同規格最低價。
- Python OneBound 歷史價資料解析器及 GitHub Actions 定時同步，支援失敗保存原資料。
- 不需要帳號或 API 金鑰即可測試手動記帳功能。

## 淘寶分享文案直接貼入（2026-10-19 更新）

- 「追蹤商品」現在可直接貼上淘寶 App 分享的**完整文案、`e.tb.cn`／`m.tb.cn` 短網址、或原始 `item.taobao.com` 商品網址**；支援從 `「商品標題」` 自動帶入名稱。
- 請在「規格」指定實際要買的顏色與尺寸，例如 **黑色／M**。同款不同規格獨立記錄，不做混價結論。
- 分享短網址本身通常沒有商品 ID。**收藏成功並不表示已取得歷史價格**。尚未解析 ID 時，可先記錄實付價；得到原始網址／ID 後，於商品明細按「補完整網址／ID」更新。
- 靜態 GitHub Pages 無法可靠跨來源存取／展開淘寶短網址，也未串接已驗證的付費淘口令解析 API，因此本功能**只負責辨識文字與保存連結，不能自動由 `tk=` 推回商品 ID，更不代表選到黑色 M 的實際結帳價格**。
- 新增 `tests/test_share_parser.cjs`，以 `node --test tests/test_share_parser.cjs` 驗證 8 個分享文案解析案例。
- 也支援網址參數 `?share=<URL 編碼分享文案>&sku=<URL 編碼規格>` 預填欄位，但**不會自動建立商品或下單**。

## ⚡ 最快測試（不需 API）

1. 下載 ZIP 並解壓縮，開啟 `index.html`，在左側新增商品。
2. 商品名稱任意，網址可貼 `https://item.taobao.com/item.htm?id=817241051574`，規格填「黑色單件」。
3. 在「記錄價格」填入日期與實付價，或在「匯入歷史價格」貼上以下**虛構測試值**，匯入類型選「到手價／實付價」：

   ```csv
   2026-09-10,499
   2026-09-20,469
   2026-10-10,599
   2026-10-19,479
   ```

4. 檢查顯示：最新 ¥479、較早最低 ¥469、不是已記錄低點（+2.13%）。樣本不足時會另外提醒。
5. 另可在「匯入報價 JSON」選 `tests/fixtures/demo_provider_history.json`，僅用於驗證第三方**參考價**圖線；測試資料會顯示標籤，**不可當作實際行情**。
6. 瀏覽器 localStorage 只能儲存單機資料；清除網站資料可能遺失紀錄，請使用完整備份 JSON。

如希望測試「同步專案紀錄」按鈕，須啟動本機 HTTP 伺服器：

```sh
cd Taobao-Price-Analyzer
python -m http.server 8000
```

開啟 `http://localhost:8000`（不建議從其他裝置直接開放本機網路）。未設定 API 時同步只會載入 `data/provider_history.json` 空資料，不會聲稱實際查到價格。

## GitHub Pages 部署（需自行建立一個新儲存庫）

1. 在 GitHub 新增一個**獨立**儲存庫，建議名稱 `Taobao-Price-Analyzer`；不要上傳到既有股票分析專案。
2. 將 ZIP 根目錄內檔案**包含隱藏的 `.github/` 目錄**上傳到新儲存庫的 `main` 分支。
3. GitHub `Settings → Pages → Build and deployment → Deploy from a branch → main / (root)`。
4. Pages 可能需要數分鐘啟用；網址通常為 `https://<你的使用者名稱>.github.io/Taobao-Price-Analyzer/`（以 GitHub 畫面提供的網址為準）。
5. 此時**不需要 API**，手動記帳、CSV 匯入、圖表等功能即可在網站使用。

> ⚠️ GitHub Pages 用靜態檔案提供網站，並不會自動讀取你的淘寶帳號、購物車，也不能直接安全保存 API 金鑰。此版本資料優先存在瀏覽器 localStorage，無跨手機同步功能。

## 連接第三方歷史價格 API（選用）

OneBound 文件：https://open.onebound.cn/help/api/taobao.item_history_price.html

**先確認 API 訂閱費用、資料權利及是否允許將結果發布在公開 GitHub 儲存庫／GitHub Pages**。不允許公開再散布時，請不要在公開儲存庫啟用此功能。此版本僅供在有合法授權的前提下做個人比價研究。

1. 自行取得 OneBound API `key` 和 `secret`（**本專案未附**）。
2. GitHub `Settings → Secrets and variables → Actions → New repository secret`，分別加入 `ONEBOUND_KEY`、`ONEBOUND_SECRET`；**不要**放在 `index.html`、`config/watchlist.json` 或任何公開檔案。
3. 在網站新增商品，按「**複製監控清單 JSON**」。到新儲存庫編輯 `config/watchlist.json`，貼上內容。例如：

   ```json
   [
     {"item_id": "817241051574", "name": "待比較商品"}
   ]
   ```

   此 ID 只是網址解析與文件格式範例，**不代表已查得實際價格**。最多 40 個商品 ID，同一 ID 不必因規格重複添加。
4. `Actions → 淘寶歷史參考報價同步 → Run workflow`，等待 GitHub 顯示成功；也可在 Actions Log 中查看錯誤訊息。
5. 工作流預設每天臺灣時間 **09:17 與 17:17** 嘗試抓取，資料會寫到 `data/provider_history.json`。在網站按「同步專案紀錄」。
6. 後續收藏新商品並不會自動修改 GitHub 監控清單；必須再更新 `config/watchlist.json`。這是為了避免在純前端網頁暴露 GitHub 寫入權杖。

### 自己在電腦執行同步

```sh
cd Taobao-Price-Analyzer
export ONEBOUND_KEY='你的 Key'
export ONEBOUND_SECRET='你的 Secret'
python scripts/price_provider.py
```

Windows PowerShell 可用 `$env:ONEBOUND_KEY='...'`，`$env:ONEBOUND_SECRET='...'`。

**此 API 的文件範例使用文字描述歷史價**，有「當前價」、「需領券」、「合單件價格」、「滿額優惠」等混雜欄位，因此解析器只把可辨識的**商品級參考報價**寫入 `listed`，絕不填成 `paid`。報價若是價區間、純券門檻、不可解析、日期錯誤或商品 ID 不符都會略過／報錯。API 若額度耗盡或格式改變，不會默默造出歷史價格。

GitHub Actions 依排程啟動不保證精準時間；公開儲存庫長期無活動可能停用定時工作流程。GitHub Pages 沒有購物車登入功能，淘寶商品價格、運費、優惠資格也可能因地區及會員身份而異。

## 測試指令

```sh
python -m unittest discover -s tests -v
```

執行上述測試指令即可。`tests/fixtures/` 所有價格均為**人工建立的測試資料**，**沒有抓到實際淘寶行情**。

## 目前限制與可能優化

- 尚未具備公開、免費且經過實際驗證的淘寶歷史成交價 API，因此無金鑰時不提供「一鍵自動查價」。
- 第三方資料可能混合不同規格，**僅顯示商品級參考報價，不能做同 SKU 最終實付史低的結論**。
- 真正的會員價、跨境運費、結帳支付折扣必須依個別帳號的結帳頁人工核對。
- 沒有推播、跨裝置帳號或交易結帳功能。
- 手動輸入歷史資料同樣需要確認來源可信度，系統只能根據已觀測樣本分析。
- GitHub Pages 網站和已提交的 `data/` 是公開可讀的（若設為公開）。**不要把真實購買明細、會員資訊、API 密鑰放入儲存庫。**
