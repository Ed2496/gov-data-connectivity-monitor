# 連線監測遷移 GitHub Actions 設定指南

## 為什麼要遷移？

Kimi 沙箱環境會在排程觸發之間被回收，檔案曾兩度遺失（8/12–8/21、8/23–8/25），且每一次排程執行都會消耗 Kimi token。遷移到 **GitHub Actions** 後：

- **零 Kimi token**：監測、報告產生完全在 GitHub 免費額度內執行（公開儲存庫不限量）。
- **資料永不遺失**：紀錄以 git commit 保存在儲存庫，每次執行都有版本歷史。
- **功能不變**：每日 09:00／15:00／21:00 測兩站、自動產 md + html 報告，2026-09-01 起自動產十天總報告。

## 遷移包內容

```
├── .github/workflows/connectivity_monitor.yml   # GitHub Actions 工作流程
├── scripts/connectivity_test.sh                 # 兩站連線測試腳本
├── scripts/build_reports.py                     # 報告產生器（md + html + 總報告）
├── connectivity_log.csv                         # 既有紀錄（含 2026-08-26 量測）
├── connectivity_report.md                       # 報告（每日自動更新）
└── index.html                                   # HTML 彙整報告（可供 Pages 預覽）
```

## 設定步驟（約 5 分鐘）

1. **建立儲存庫**：到 github.com 新增一個 repository（Public 可享免費無限 Actions 額度；Private 每月 2,000 分鐘免費也足夠）。
2. **上傳檔案**：解開 `連線監測_GitHub_Actions_遷移包.zip`，把**所有檔案（含 `.github` 隱藏目錄）**推到儲存庫根目錄：
   ```bash
   git init && git add -A && git commit -m "init"
   git remote add origin https://github.com/你的帳號/儲存庫名稱.git
   git push -u origin main
   ```
   也可以直接在 GitHub 網頁用「Add file → Upload files」上傳。
3. **確認啟用**：到儲存庫的 **Actions** 分頁，應看到「政府資料平台連線監測」工作流程；可先點「Run workflow」手動跑一次驗證。
4. **（可選）開啟網頁預覽**：Settings → Pages → Source 選「Deploy from a branch」、分支選 `main` / 根目錄，之後就能用 `https://你的帳號.github.io/儲存庫名稱/` 隨時看 HTML 報告。

## 重要注意事項

- **排程時區**：workflow 的 cron 是 UTC，`0 1,7,13 * * *` 對應台北 09:00／15:00／21:00。GitHub 排程高峰時可能延遲數分鐘，屬正常。
- **地區封鎖風險**：8/26 實測兩站從境外連線均逾時（DNS 正常、TCP 無回應，對照組 data.gov.tw 正常），判斷這兩站可能封鎖境外／資料中心 IP。GitHub Actions 主機位於美國 Azure，**可能同樣連不上**。若遷移後持續 FAIL 而您從台灣本機瀏覽器可正常開啟，即為地區封鎖，屆時建議改在台灣本機用「工作排程器（Windows）／cron（Mac、Linux）」跑同一支 `scripts/connectivity_test.sh` 即可。
- **停止 Kimi 端排程**：Kimi 上的每日排程已在遷移時刪除，不會再消耗 token。
- **監測期滿**：2026-09-01 最後一輪後 workflow 會自動產出 `connectivity_final_report.md`（十天總報告）。之後若不再需要，到 Actions 分頁停用 workflow 或刪除儲存庫即可。

## 本機手動執行（任何電腦都可用）

```bash
bash scripts/connectivity_test.sh     # 測兩站、寫入 connectivity_log.csv
python3 scripts/build_reports.py      # 產生 connectivity_report.md 與 index.html
```
