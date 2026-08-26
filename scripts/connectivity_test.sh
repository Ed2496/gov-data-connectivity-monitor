#!/usr/bin/env bash
# ============================================================
# 連線監測腳本（GitHub Actions 版）
# 監測目標：
#   1. KCG 高雄開放資料平台 — https://data.kcg.gov.tw/
#   2. MOL 勞動部統計資料庫 — https://statfy.mol.gov.tw/statistic_DB.aspx
# 輸出：附加測試紀錄至儲存庫根目錄 connectivity_log.csv
# ============================================================
set -u
cd "$(dirname "$0")/.."   # 切到儲存庫根目錄

LOG="connectivity_log.csv"
TS="$(TZ='Asia/Taipei' date '+%Y-%m-%d %H:%M:%S')（台北時間）"
TIMEOUT=30

if [ ! -f "$LOG" ]; then
  echo "timestamp,site,url,http_code,response_time_s,result,note" > "$LOG"
fi

test_site () {
  local site="$1" url="$2"
  local tmp_err out err code rtime result note
  tmp_err="$(mktemp)"
  out="$(curl -sS -o /dev/null -w '%{http_code} %{time_total}' -m "$TIMEOUT" -L "$url" 2>"$tmp_err")"
  err="$(cat "$tmp_err")"; rm -f "$tmp_err"
  code="${out%% *}"
  rtime="${out##* }"
  rtime="$(printf '%.3f' "$rtime" 2>/dev/null || echo "$rtime")"

  if [ "$code" = "200" ]; then
    result="OK";    note="HTTP 200 正常回應"
  elif echo "$err" | grep -qi "timed out"; then
    result="FAIL";  note="連線逾時（${TIMEOUT}s 無回應）"
  elif echo "$err" | grep -qi "Could not resolve"; then
    result="FAIL";  note="DNS 解析失敗"
  elif [ "$code" = "000" ]; then
    result="FAIL";  note="$(echo "$err" | tr ',;' '  ' | cut -c1-60)"
  else
    result="FAIL";  note="HTTP ${code} 異常回應"
  fi

  echo "${TS},${site},${url},${code},${rtime},${result},${note}" >> "$LOG"
  printf '%s | %-3s | http=%-3s | %ss | %-4s | %s\n' "$TS" "$site" "$code" "$rtime" "$result" "$note"
}

echo "=== 連線監測開始：$TS ==="
test_site "KCG" "https://data.kcg.gov.tw/"
test_site "MOL" "https://statfy.mol.gov.tw/statistic_DB.aspx"
echo "=== 監測完成 ==="
