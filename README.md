# 電程 ChargePath 支援網站

無建置相依套件的 GitHub Pages 靜態網站。

- 支援網址：https://amonstudioapp.github.io/chargepath-support/
- 隱私權政策：https://amonstudioapp.github.io/chargepath-support/privacy.html
- 儲存庫：https://github.com/amonstudioapp/chargepath-support

- `index.html`：支援信箱、常見問題、問題回報資訊。
- `privacy.html`：依 App 內隱私權政策整理，補充網站託管說明。
- `styles.css`：共用響應式版面。
- `assets/app-icon.png`：電程 App 圖示。
- `.nojekyll`：讓 GitHub Pages 直接發布靜態檔案。

## 本機預覽

在此目錄執行 `python3 -m http.server 8765 --bind 127.0.0.1`，開啟 `http://127.0.0.1:8765/`。

## GitHub Pages

將本目錄內容推送至獨立的網站儲存庫。在 Settings → Pages 選擇 Deploy from a branch、`main` 分支與 `/ (root)` 目錄。不要將 App 原始碼、帳本或測試資料加入此儲存庫。

發布後，App Store Connect 的 Support URL 使用網站首頁；Privacy Policy URL 使用網站的 `privacy.html`。以 GitHub Pages 實際回傳並可公開存取的網址為準。

支援信箱：amonstudioapp@gmail.com。所有聯絡連結皆開啟使用者的郵件程式，不會自動寄信。
