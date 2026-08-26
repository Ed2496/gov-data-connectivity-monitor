#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
連線監測報告產生器（GitHub Actions 版）
讀取儲存庫根目錄 connectivity_log.csv
產生：connectivity_report.md（每日報告＋累計統計）
      index.html（HTML 彙整報告，可供 GitHub Pages 預覽）
      connectivity_final_report.md（2026-09-01 起自動產出十天總報告）
"""
import csv
import html
import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "connectivity_log.csv")
MD_OUT = os.path.join(ROOT, "connectivity_report.md")
HTML_OUT = os.path.join(ROOT, "index.html")
FINAL_OUT = os.path.join(ROOT, "connectivity_final_report.md")

SITE_NAMES = {
    "KCG": "KCG 高雄開放資料平台",
    "MOL": "MOL 勞動部統計資料庫",
}
SITE_URLS = {
    "KCG": "https://data.kcg.gov.tw/",
    "MOL": "https://statfy.mol.gov.tw/statistic_DB.aspx",
}
SITE_ORDER = ["KCG", "MOL"]
PERIOD = "2026-08-23 ～ 2026-09-01"
FINAL_DATE = datetime(2026, 9, 1).date()
TW = timezone(timedelta(hours=8))


def load_rows():
    rows = []
    if os.path.exists(LOG):
        with open(LOG, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows


def stats_for(rows, site):
    rs = [r for r in rows if r["site"] == site]
    total = len(rs)
    ok = sum(1 for r in rs if r["result"] == "OK")
    fail = total - ok
    rate = (ok / total * 100) if total else 0.0
    times = [float(r["response_time_s"]) for r in rs if r["response_time_s"]]
    avg = sum(times) / len(times) if times else 0.0
    ok_times = [float(r["response_time_s"]) for r in rs if r["result"] == "OK" and r["response_time_s"]]
    avg_ok = sum(ok_times) / len(ok_times) if ok_times else None
    return {"total": total, "ok": ok, "fail": fail, "rate": rate,
            "avg": avg, "avg_ok": avg_ok, "last": rs[-1] if rs else None}


def daily_groups(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r["timestamp"][:10]].append(r)
    return dict(sorted(groups.items()))


def build_md(rows, now):
    total = len(rows)
    ok_all = sum(1 for r in rows if r["result"] == "OK")
    rate_all = (ok_all / total * 100) if total else 0.0

    stat_lines = []
    for site in SITE_ORDER:
        s = stats_for(rows, site)
        avg_ok = f"{s['avg_ok']:.3f}s" if s["avg_ok"] is not None else "—"
        last = f"{s['last']['result']}（{s['last']['timestamp'][:16]}）" if s["last"] else "—"
        stat_lines.append(
            f"| {SITE_NAMES[site]} | {s['total']} | {s['ok']} | {s['fail']} "
            f"| {s['rate']:.1f}% | {avg_ok} | {last} |")
    stat_lines.append(
        f"| **合計** | **{total}** | **{ok_all}** | **{total - ok_all}** | **{rate_all:.1f}%** | — | — |")

    day_sections = []
    for day, rs in daily_groups(rows).items():
        lines = [f"### {day}", "",
                 "| 時間（台北） | 網站 | HTTP | 回應時間 | 結果 | 備註 |",
                 "| --- | --- | ---: | ---: | --- | --- |"]
        for r in rs:
            lines.append(
                f"| {r['timestamp']} | {SITE_NAMES.get(r['site'], r['site'])} "
                f"| {r['http_code']} | {r['response_time_s']}s | {r['result']} | {r['note']} |")
        day_sections.append("\n".join(lines))

    return f"""# 政府資料平台連線監測報告

最後更新：{now}（台北時間）

## 監測概要

| 項目 | 說明 |
| --- | --- |
| 監測期間 | {PERIOD} |
| 監測頻率 | 每日 09:00／15:00／21:00（台北時間） |
| 監測目標 1 | KCG 高雄開放資料平台 — {SITE_URLS['KCG']} |
| 監測目標 2 | MOL 勞動部統計資料庫 — {SITE_URLS['MOL']} |
| 測試方法 | curl HTTPS GET（跟隨轉址），逾時上限 30 秒 |
| 判定標準 | HTTP 200 = OK；其餘 = FAIL |
| 執行環境 | GitHub Actions（ubuntu-latest） |

## 累計統計（依實際量測紀錄）

| 網站 | 累計次數 | 成功 | 失敗 | 成功率 | 平均回應（成功時） | 最近結果 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(stat_lines)}

## 每日日誌

{chr(10) + chr(10).join(day_sections) if day_sections else '尚無紀錄'}

---

*本報告由 GitHub Actions 自動產生。*
"""


def build_final_md(rows, now):
    total = len(rows)
    ok_all = sum(1 for r in rows if r["result"] == "OK")
    rate_all = (ok_all / total * 100) if total else 0.0
    days = daily_groups(rows)

    site_lines = []
    for site in SITE_ORDER:
        s = stats_for(rows, site)
        avg_ok = f"{s['avg_ok']:.3f}s" if s["avg_ok"] is not None else "—"
        site_lines.append(
            f"| {SITE_NAMES[site]} | {s['total']} | {s['ok']} | {s['fail']} "
            f"| {s['rate']:.1f}% | {s['avg']:.3f}s | {avg_ok} |")

    day_lines = []
    for day, rs in days.items():
        for site in SITE_ORDER:
            srs = [r for r in rs if r["site"] == site]
            if not srs:
                continue
            ok = sum(1 for r in srs if r["result"] == "OK")
            day_lines.append(f"| {day} | {SITE_NAMES[site]} | {len(srs)} | {ok} "
                             f"| {len(srs) - ok} | {ok / len(srs) * 100:.1f}% |")

    return f"""# 政府資料平台連線監測 — 十天總報告

產出時間：{now}（台北時間）
監測期間：{PERIOD}
實際監測天數：{len(days)} 天　｜　總檢測次數：{total}　｜　整體成功率：{rate_all:.1f}%

## 一、站點總結

| 網站 | 總次數 | 成功 | 失敗 | 成功率 | 平均回應（全部） | 平均回應（成功時） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(site_lines)}

## 二、逐日統計

| 日期 | 網站 | 當日次數 | 成功 | 失敗 | 當日成功率 |
| --- | --- | ---: | ---: | ---: | ---: |
{chr(10).join(day_lines)}

## 三、完整量測紀錄

詳見 `connectivity_log.csv` 與 `connectivity_report.md`。

---

*十天監測期間結束，本總報告由 GitHub Actions 自動產出。*
"""


def build_html(rows, now):
    total = len(rows)
    ok_all = sum(1 for r in rows if r["result"] == "OK")
    rate_all = (ok_all / total * 100) if total else 0.0

    cards = []
    for site in SITE_ORDER:
        s = stats_for(rows, site)
        if s["last"]:
            last = s["last"]
            cls = "ok" if last["result"] == "OK" else "fail"
            txt = "正常" if last["result"] == "OK" else "異常"
            body = (f"最近檢測：{html.escape(last['timestamp'])}<br>結果："
                    f"<span class='badge {'ok' if last['result']=='OK' else 'fail'}'>"
                    f"{'✓ OK' if last['result']=='OK' else '✗ FAIL'}</span>　"
                    f"HTTP {html.escape(last['http_code'])}　{html.escape(last['response_time_s'])}s<br>"
                    f"<span class='note'>{html.escape(last['note'])}</span>")
        else:
            cls, txt, body = "unknown", "無資料", "尚無監測紀錄"
        cards.append(f"""
      <div class="card {cls}">
        <div class="card-head"><h2>{SITE_NAMES[site]}</h2><span class="status-dot {cls}"></span></div>
        <div class="url">{SITE_URLS[site]}</div>
        <div class="big-status">{txt}</div>
        <div class="card-body">{body}</div>
        <div class="metrics">
          <div><span class="num">{s['total']}</span><span class="lbl">累計次數</span></div>
          <div><span class="num">{s['rate']:.1f}%</span><span class="lbl">成功率</span></div>
          <div><span class="num">{s['avg']:.2f}s</span><span class="lbl">平均回應</span></div>
        </div>
      </div>""")

    stat_rows = []
    for site in SITE_ORDER:
        s = stats_for(rows, site)
        avg_ok = f"{s['avg_ok']:.3f}s" if s["avg_ok"] is not None else "—"
        last = f"{s['last']['result']}（{html.escape(s['last']['timestamp'][:16])}）" if s["last"] else "—"
        stat_rows.append(
            f"<tr><td>{SITE_NAMES[site]}</td><td class='r'>{s['total']}</td><td class='r'>{s['ok']}</td>"
            f"<td class='r'>{s['fail']}</td><td class='r'>{s['rate']:.1f}%</td>"
            f"<td class='r'>{avg_ok}</td><td>{last}</td></tr>")

    log_rows = []
    for r in reversed(rows):
        cls = "row-ok" if r["result"] == "OK" else "row-fail"
        bg = '<span class="badge ok">✓ OK</span>' if r["result"] == "OK" else '<span class="badge fail">✗ FAIL</span>'
        log_rows.append(
            f"<tr class='{cls}'><td>{html.escape(r['timestamp'])}</td>"
            f"<td>{html.escape(SITE_NAMES.get(r['site'], r['site']))}</td>"
            f"<td class='r'>{html.escape(r['http_code'])}</td>"
            f"<td class='r'>{html.escape(r['response_time_s'])}s</td>"
            f"<td>{bg}</td><td>{html.escape(r['note'])}</td></tr>")
    if not log_rows:
        log_rows.append("<tr><td colspan='6' class='empty'>尚無紀錄</td></tr>")

    with open(LOG, encoding="utf-8") as f:
        raw_csv = html.escape(f.read()) if os.path.exists(LOG) else ""

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>政府資料平台連線監測報告</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
         background:#f0f4f8; color:#1e293b; line-height:1.6; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:32px 20px 64px; }}
  header {{ background:linear-gradient(135deg,#0f3d6e,#1565a8); color:#fff;
           border-radius:14px; padding:28px 32px; margin-bottom:24px; }}
  header h1 {{ font-size:1.6rem; }}
  header p {{ opacity:.85; font-size:.9rem; margin-top:6px; }}
  .gen {{ float:right; font-size:.78rem; opacity:.75; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
           gap:18px; margin-bottom:28px; }}
  .card {{ background:#fff; border-radius:12px; padding:20px 22px;
          box-shadow:0 2px 8px rgba(30,41,59,.08); border-top:5px solid #94a3b8; }}
  .card.ok {{ border-top-color:#16a34a; }}
  .card.fail {{ border-top-color:#dc2626; }}
  .card-head {{ display:flex; justify-content:space-between; align-items:center; }}
  .card h2 {{ font-size:1.05rem; }}
  .status-dot {{ width:12px; height:12px; border-radius:50%; background:#94a3b8; }}
  .status-dot.ok {{ background:#16a34a; box-shadow:0 0 0 4px rgba(22,163,74,.15); }}
  .status-dot.fail {{ background:#dc2626; box-shadow:0 0 0 4px rgba(220,38,38,.15); }}
  .url {{ font-size:.78rem; color:#64748b; word-break:break-all; margin-top:2px; }}
  .big-status {{ font-size:1.9rem; font-weight:700; margin:10px 0 6px; }}
  .card.ok .big-status {{ color:#16a34a; }}
  .card.fail .big-status {{ color:#dc2626; }}
  .card-body {{ font-size:.88rem; color:#334155; min-height:66px; }}
  .note {{ color:#94a3b8; font-size:.8rem; }}
  .metrics {{ display:flex; border-top:1px solid #e2e8f0; margin-top:12px; padding-top:12px; }}
  .metrics > div {{ flex:1; text-align:center; }}
  .metrics .num {{ display:block; font-size:1.15rem; font-weight:700; color:#0f3d6e; }}
  .metrics .lbl {{ font-size:.75rem; color:#64748b; }}
  .badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem; font-weight:600; }}
  .badge.ok {{ background:#dcfce7; color:#15803d; }}
  .badge.fail {{ background:#fee2e2; color:#b91c1c; }}
  section {{ background:#fff; border-radius:12px; padding:22px 24px; margin-bottom:22px;
            box-shadow:0 2px 8px rgba(30,41,59,.08); overflow-x:auto; }}
  section h3 {{ font-size:1.05rem; margin-bottom:12px; color:#0f3d6e; }}
  table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
  th,td {{ padding:8px 10px; border-bottom:1px solid #e2e8f0; text-align:left; }}
  th {{ background:#f1f5f9; color:#475569; font-weight:600; white-space:nowrap; }}
  td.r,th.r {{ text-align:right; }}
  tr.row-fail td {{ background:#fff7f7; }}
  tr.row-ok td {{ background:#f7fff9; }}
  .empty {{ text-align:center; color:#94a3b8; }}
  footer {{ text-align:center; color:#94a3b8; font-size:.78rem; margin-top:8px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="gen">報告產生時間：{now}（台北時間）</span>
    <h1>政府資料平台連線監測報告</h1>
    <p>監測期間：{PERIOD}　｜　頻率：每日 09:00／15:00／21:00　｜　累計檢測 {total} 次，整體成功率 {rate_all:.1f}%　｜　由 GitHub Actions 自動執行</p>
  </header>

  <div class="cards">{''.join(cards)}
  </div>

  <section>
    <h3>累計統計</h3>
    <table>
      <thead><tr><th>網站</th><th class="r">累計次數</th><th class="r">成功</th><th class="r">失敗</th><th class="r">成功率</th><th class="r">平均回應（成功時）</th><th>最近結果</th></tr></thead>
      <tbody>{''.join(stat_rows)}</tbody>
    </table>
  </section>

  <section>
    <h3>監測紀錄（新→舊）</h3>
    <table>
      <thead><tr><th>時間</th><th>網站</th><th class="r">HTTP</th><th class="r">回應時間</th><th>結果</th><th>備註</th></tr></thead>
      <tbody>{''.join(log_rows)}</tbody>
    </table>
  </section>

  <footer>GitHub Actions 自動產生 ｜ 原始紀錄內嵌於本頁 ｜ 2026-09-01 起自動產出十天總報告</footer>
</div>
<script type="text/plain" id="raw-csv">{raw_csv}</script>
</body>
</html>"""


def main():
    rows = load_rows()
    now = datetime.now(TW).strftime("%Y-%m-%d %H:%M:%S")
    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write(build_md(rows, now))
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(build_html(rows, now))
    print(f"已產生 connectivity_report.md 與 index.html（{len(rows)} 筆紀錄）")
    if datetime.now(TW).date() >= FINAL_DATE:
        with open(FINAL_OUT, "w", encoding="utf-8") as f:
            f.write(build_final_md(rows, now))
        print("已產出十天總報告 connectivity_final_report.md")


if __name__ == "__main__":
    main()
