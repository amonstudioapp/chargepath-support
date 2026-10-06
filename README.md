# 電程 ChargePath 支援網站

GitHub Pages 靜態網站。Python 3.10 以上可建置；Pillow 用於產生版本分享圖，線上瀏覽不需要 JavaScript。

- [支援中心](https://amonstudioapp.github.io/chargepath-support/)
- [版本更新總覽](https://amonstudioapp.github.io/chargepath-support/updates/)
- [隱私權政策](https://amonstudioapp.github.io/chargepath-support/privacy.html)
- [網站儲存庫](https://github.com/amonstudioapp/chargepath-support)

## 版本更新怎麼呈現

總覽以最新版本、三個重點與歷史清單呈現；每版有固定網址 `updates/<version>/`，包含發布日期、功能重點、完整更新項目及前後版本導覽。各頁附分享標題與描述，也提供 `updates/feed.xml` RSS。

- `data/releases.json`：所有版本的內容來源；依語意版本排序。
- `templates/`：總覽與版本頁版型。
- `updates.css`：森林綠、米白與宋體的更新日誌版面。
- `scripts/build_updates.py`：產生靜態頁面與 RSS。
- `scripts/sync_app_store.py`：從台灣 App Store 讀取新版本。
- `tests/`：驗證資料、HTML 跳脫、網址安全、版本排序、同步與建置流程。
- `index.html`、`home.css`、`assets/app-overview.png`：首頁 App 介紹、示範畫面與 App Store 下載入口。
- `privacy.html`、`styles.css`、`assets/app-icon.png`：共用品牌與支援內容。

初始內容：1.1.0 使用 2026-10-05 台灣 App Store 公開的八項更新；1.0.0 是首版功能概覽，依既有產品說明整理，首次上架日期為 2026-10-02，不宣稱為歷史 App Store 原文。不要從內部測試 build、未發布開發紀錄推測正式版功能。

## 每次 App 改版

GitHub Actions 的 **Sync updates and publish Pages** 會每 6 小時檢查 App Store（台灣時間約 02:23、08:23、14:23、20:23；GitHub 排程可能延遲）。發現更高版本時會：

1. 驗證 App ID、版本與台灣日期，讀取官方版本更新文字。
2. 新增一筆版本內容，保留既有的人工標題、重點與歷史紀錄。
3. 通過測試後，產生總覽、專屬頁與 RSS，保存到 Git，再部署網站。

**發布新版後建議立即執行一次**：到 Actions → Sync updates and publish Pages → Run workflow。也可執行 `gh workflow run pages.yml --repo amonstudioapp/chargepath-support`。無需新增金鑰；工作流程使用 GitHub 提供的 token。

App Store Lookup 只提供當下最新版本。若兩次檢查之間連續發布多版、排程停用或服務長時間無法連線，中間版本要手動補入。版本資訊不變時不覆寫已保存內容；同一版本在商店更正文案，也請手動同步修正。本流程不自動抓取尚未公開的 TestFlight 或送審內容。

公開儲存庫長期沒有活動時，GitHub 可能停用排程（目前為 60 天），須到 Actions 重新啟用。同步失敗會讓該次工作流程失敗，既有線上網站仍保留；可在 Actions 檢查原因並重跑。參考 [GitHub 排程規則](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

## 編輯或補上版本

直接編輯 `data/releases.json`，為新版本新增一筆資料：

```json
{
  "version": "1.2.0",
  "date": "2026-10-20",
  "title": "填入這個版本的重點標題",
  "summary": "用一兩句話說明這次更新帶來的改變。",
  "source": "editorial",
  "highlights": [
    { "title": "功能重點", "description": "說明使用者可以做什麼。" }
  ],
  "sections": [
    { "title": "新增功能", "items": ["填入實際已發布的新功能。"] },
    { "title": "體驗改善", "items": ["填入實際改善或修正的項目。"] }
  ],
  "sourceNote": "必要時補充適用條件或內容來源。"
}
```

以上為格式範例，不是已發布版本。`highlights` 與 `sourceNote` 可省略；`source` 可用 `app-store` 或 `editorial`；不要貼入 HTML。版本接受 1–3 組整數（如 `2`、`2.1`、`2.1.0`），同義版本不可重複。發布日期以台灣日期填寫。

```sh
python3 -m pip install -r requirements.txt
python3 scripts/build_share_cards.py
python3 tests/run_coverage.py
python3 scripts/build_updates.py
python3 scripts/build_updates.py --check
python3 scripts/build_share_cards.py --check
python3 -m http.server 8765 --bind 127.0.0.1
```

開啟 `http://127.0.0.1:8765/updates/`。推送內容至 `main` 後會自動重新建置及部署。**不要直接編輯 `updates/` 內產生的 HTML**；它們會由版型和資料重建。移除錯誤版本時，建置只清理已標記為自動產生的舊版頁，保留手動檔案。

測試包括單元／整合測試與每個 Python 模組至少 80% 行覆蓋率檢查。請先安裝 requirements.txt 的建置依賴。首次發布亦已驗證桌面、390px 與 320px 的瀏覽器導覽與無橫向溢位。

## GitHub Pages 部署

Settings → Pages → Source 使用 **GitHub Actions**。`.github/workflows/pages.yml` 在 `main` 推送、手動執行或排程時運作。只有網站 HTML、CSS、圖示與 `updates/` 會進入 Pages artifact；不部署 App 原始碼、測試資料或內部筆記。Python 腳本與測試本身為公開網站建置工具，不含 App 內部資料。

本儲存庫的遠端內容是網站發布來源；App 專案中的 `docs/support-site` 為本機副本。修改前先取得遠端最新內容，避免覆蓋自動同步的新版本。

App Store Connect 的 Support URL 與 Privacy Policy URL 維持原網址。支援信箱：amonstudioapp@gmail.com。聯絡連結開啟使用者郵件程式，不會自動寄信。

## Facebook 與社群分享縮圖

首頁、更新總覽與每個版本頁在原始 HTML head 提供完整 Open Graph 標記，包含絕對 HTTPS URL、secure_url、MIME、寬高與替代文字，不依賴 JavaScript。所有分享圖都是 1200 × 630 PNG。

- 首頁沿用 `assets/chargepath-share-v1.png` 品牌圖。
- 版本頁使用 `assets/updates/<version>-v1.png`，呈現「電程 ChargePath」、「版本更新」與大字版本號。
- 更新總覽使用目前最新版本的分享圖。

`scripts/build_share_cards.py` 從 releases.json 讀取版本，以 `assets/update-share-base.png` 固定品牌底圖加上數字；數字使用 Pillow 內附字型，無需系統字型。GitHub Actions 自動同步新版本時也會產生並保存圖片。相關測試驗證每版圖片連結、尺寸與建置流程。

首頁品牌圖來源為 `templates/share-card.html`，版本圖則由固定底圖與數字組成。若重設圖片設計，請使用新的檔名後綴並同步修改產生器、版型及測試，避免沿用舊圖片快取。

既有網址若已被 Facebook 快取，部署後至 [Meta 分享偵錯工具](https://developers.facebook.com/tools/debug/) 輸入完整網址，點「再次抓取」，以工具中的連結預覽確認圖片。網頁 HTTP 200 只代表公開可讀，不能單獨證明 Facebook 快取已更新。
