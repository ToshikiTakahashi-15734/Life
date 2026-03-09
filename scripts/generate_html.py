#!/usr/bin/env python3
"""JSON データから静的HTMLページを直接生成 - テーブル表示版"""

import json
import calendar
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape

JST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = BASE_DIR / "public"

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]


def load_trends(date_str=None):
    if date_str is None:
        date_str = datetime.now(JST).strftime("%Y-%m-%d")
    path = DATA_DIR / date_str / "trends.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_dates():
    dates = []
    if DATA_DIR.exists():
        for d in DATA_DIR.iterdir():
            if d.is_dir() and (d / "trends.json").exists():
                dates.append(d.name)
    return sorted(dates, reverse=True)


def group_by_source(articles):
    sources = {}
    for a in articles:
        src = a["source"]
        if src not in sources:
            sources[src] = {"icon": a.get("source_icon", ""), "articles": []}
        sources[src]["articles"].append(a)
    return sources


def render_table_row(idx, a):
    title = escape(a["title"])
    url = escape(a["url"])
    source = escape(a["source"])
    icon = a.get("source_icon", "")
    summary = escape(a.get("summary", "") or "")
    score = a.get("score", 0)
    comments = a.get("comments", 0)

    meta = ""
    if score:
        meta += f'<span class="score">&#9650;{score}</span>'
    if comments:
        meta += f' <span class="comments">&#128172;{comments}</span>'

    return f'''<tr>
  <td class="col-num">{idx}</td>
  <td class="col-source"><span class="source-badge">{icon} {source}</span></td>
  <td class="col-title"><a href="{url}" target="_blank" rel="noopener">{title}</a>{meta}</td>
  <td class="col-summary">{summary}</td>
</tr>'''


def render_source_table(src_name, icon, articles):
    rows = "\n".join(render_table_row(i + 1, a) for i, a in enumerate(articles))
    return f'''<section class="source-section">
  <h2 class="source-title">{icon} {escape(src_name)} <span class="count">({len(articles)})</span></h2>
  <table class="trend-table">
    <thead>
      <tr>
        <th class="col-num">#</th>
        <th class="col-source">Source</th>
        <th class="col-title">Title</th>
        <th class="col-summary">Summary</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</section>'''


def render_calendar(dates_set):
    """月別カレンダーをHTML生成。データがある日はリンク付き"""
    # 月でグルーピング
    months = defaultdict(set)
    for d in dates_set:
        parts = d.split("-")
        ym = f"{parts[0]}-{parts[1]}"
        months[ym].add(int(parts[2]))

    sorted_months = sorted(months.keys(), reverse=True)
    html = ""
    for ym in sorted_months:
        year, month = int(ym.split("-")[0]), int(ym.split("-")[1])
        days_with_data = months[ym]
        cal = calendar.monthcalendar(year, month)

        month_html = f'<div class="cal-month"><h3>{year}年{month}月</h3><table class="cal-table"><thead><tr>'
        for wd in WEEKDAYS_JA:
            cls = ' class="cal-weekend"' if wd in ("土", "日") else ""
            month_html += f"<th{cls}>{wd}</th>"
        month_html += "</tr></thead><tbody>"

        for week in cal:
            month_html += "<tr>"
            for i, day in enumerate(week):
                if day == 0:
                    month_html += '<td class="cal-empty"></td>'
                elif day in days_with_data:
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    cls = "cal-day cal-has-data"
                    if i >= 5:
                        cls += " cal-weekend"
                    month_html += f'<td class="{cls}"><a href="archive/{date_str}.html">{day}</a></td>'
                else:
                    cls = "cal-day"
                    if i >= 5:
                        cls += " cal-weekend"
                    month_html += f'<td class="{cls}">{day}</td>'
            month_html += "</tr>"

        month_html += "</tbody></table></div>"
        html += month_html

    return html


def css():
    return '''<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:#0f1117;color:#e0e0e0;line-height:1.6}
header{background:linear-gradient(135deg,#1a1c2e,#2d1b4e);padding:24px 32px;
  border-bottom:1px solid #2a2d3e}
header h1{font-size:1.6rem;color:#fff}
header p{color:#9ca3af;font-size:.85rem;margin-top:4px}
.container{max-width:1400px;margin:0 auto;padding:24px}
.stats{display:flex;gap:20px;margin-top:8px}
.stats span{background:#1e2033;padding:4px 12px;border-radius:20px;font-size:.8rem;color:#9ca3af}

/* Source section */
.source-section{margin-bottom:28px}
.source-title{font-size:1.1rem;color:#c4b5fd;margin-bottom:8px;padding-bottom:6px;
  border-bottom:1px solid #2a2d3e;display:flex;align-items:center;gap:8px}
.source-title .count{font-size:.8rem;color:#6b7280;font-weight:normal}

/* Table */
.trend-table{width:100%;border-collapse:collapse;font-size:.88rem}
.trend-table thead{background:#161829}
.trend-table th{text-align:left;padding:8px 12px;color:#9ca3af;font-weight:600;
  border-bottom:2px solid #2a2d3e;white-space:nowrap;font-size:.78rem;text-transform:uppercase;letter-spacing:.5px}
.trend-table td{padding:7px 12px;border-bottom:1px solid #1e2033;vertical-align:top}
.trend-table tbody tr:hover{background:#1a1c2e}
.col-num{width:36px;color:#4b5563;text-align:center}
.col-source{width:140px;white-space:nowrap}
.col-title{min-width:280px}
.col-summary{color:#9ca3af;font-size:.82rem;max-width:360px}
.source-badge{font-size:.78rem;color:#9ca3af}
.trend-table a{color:#e2e8f0;text-decoration:none}
.trend-table a:hover{color:#a78bfa;text-decoration:underline}
.score{color:#f59e0b;font-size:.75rem;margin-left:8px}
.comments{color:#60a5fa;font-size:.75rem}

/* Calendar Archive */
.archive-section{margin-top:36px}
.archive-section>h2{font-size:1.1rem;color:#c4b5fd;margin-bottom:16px}
.cal-grid{display:flex;flex-wrap:wrap;gap:20px}
.cal-month{background:#1a1c2e;border:1px solid #2a2d3e;border-radius:8px;padding:16px;min-width:280px}
.cal-month h3{font-size:.9rem;color:#e2e8f0;margin-bottom:8px;text-align:center}
.cal-table{width:100%;border-collapse:collapse;font-size:.82rem}
.cal-table th{padding:4px;text-align:center;color:#6b7280;font-weight:normal;font-size:.72rem}
.cal-table td{padding:4px;text-align:center;height:28px}
.cal-day{color:#4b5563}
.cal-has-data{background:#1e1040;border-radius:4px}
.cal-has-data a{color:#a78bfa;text-decoration:none;font-weight:600;display:block}
.cal-has-data a:hover{color:#c4b5fd;background:#2d1b4e;border-radius:4px}
.cal-has-data:hover{background:#2d1b4e}
.cal-weekend{color:#4b5563}
.cal-empty{color:transparent}

/* Recent list */
.recent-list{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.recent-list a{display:inline-block;padding:6px 14px;background:#1e2033;border:1px solid #2a2d3e;
  border-radius:6px;color:#60a5fa;text-decoration:none;font-size:.82rem;transition:all .2s}
.recent-list a:hover{background:#2d1b4e;border-color:#7c3aed;color:#c4b5fd}
.recent-list a.today{background:#2d1b4e;border-color:#7c3aed;color:#c4b5fd;font-weight:600}

.empty{text-align:center;padding:60px 20px;color:#6b7280}
.back-link{display:inline-block;margin-bottom:16px;color:#60a5fa;text-decoration:none;font-size:.9rem}
.back-link:hover{text-decoration:underline}
</style>'''


def format_date_label(date_str):
    """2026-03-09 → 2026/03/09 (日)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    wd = WEEKDAYS_JA[dt.weekday()]
    return f'{dt.strftime("%Y/%m/%d")} ({wd})'


def generate_home():
    today = datetime.now(JST).strftime("%Y-%m-%d")
    data = load_trends(today)
    dates = get_all_dates()
    generated = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")

    body_content = ""
    if data and data["articles"]:
        sources = group_by_source(data["articles"])
        for src_name, src_data in sources.items():
            body_content += render_source_table(src_name, src_data["icon"], src_data["articles"])
        stats = f'''<div class="stats">
  <span>Total: {data["total_count"]} articles</span>
  <span>Sources: {len(sources)}</span>
</div>'''
    else:
        body_content = '<div class="empty"><p>No data for today yet.</p><p>Run <code>python scripts/run.py</code> to collect trends.</p></div>'
        stats = ""

    # 直近の日付リスト
    recent_html = ""
    if dates:
        links = []
        for d in dates[:14]:
            label = format_date_label(d)
            cls = ' class="today"' if d == today else ""
            links.append(f'<a href="archive/{d}.html"{cls}>{label}</a>')
        recent_html = f'<div class="recent-list">{"".join(links)}</div>'

    # カレンダー
    cal_html = render_calendar(set(dates))
    archive_section = ""
    if dates:
        archive_section = f'''<section class="archive-section">
  <h2>Archive</h2>
  {recent_html}
  <div class="cal-grid">{cal_html}</div>
</section>'''

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IT Trend Dashboard - {today}</title>
{css()}
</head>
<body>
<header>
  <h1>IT Trend Dashboard</h1>
  <p>{format_date_label(today)} | Updated: {generated}</p>
  {stats}
</header>
<main class="container">
{body_content}
{archive_section}
</main>
</body>
</html>'''

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    with open(PUBLIC_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated: {PUBLIC_DIR / 'index.html'}")


def generate_archive_page(date_str):
    data = load_trends(date_str)
    if not data:
        return

    sources = group_by_source(data["articles"])
    body_content = ""
    for src_name, src_data in sources.items():
        body_content += render_source_table(src_name, src_data["icon"], src_data["articles"])

    label = format_date_label(date_str)

    # 前後の日付リンク
    all_dates = get_all_dates()
    idx = all_dates.index(date_str) if date_str in all_dates else -1
    nav = ""
    if idx >= 0:
        prev_link = f'<a href="{all_dates[idx - 1]}.html">&larr; {format_date_label(all_dates[idx - 1])}</a>' if idx > 0 else '<span></span>'
        next_link = f'<a href="{all_dates[idx + 1]}.html">{format_date_label(all_dates[idx + 1])} &rarr;</a>' if idx < len(all_dates) - 1 else '<span></span>'
        nav = f'<div style="display:flex;justify-content:space-between;margin-bottom:16px;font-size:.88rem">{prev_link}{next_link}</div>'

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IT Trends - {label}</title>
{css()}
</head>
<body>
<header>
  <h1>IT Trend Dashboard</h1>
  <p>{label} | {data["total_count"]} articles</p>
</header>
<main class="container">
<a href="../index.html" class="back-link">&larr; Back to Home</a>
{nav}
{body_content}
</main>
</body>
</html>'''

    archive_dir = PUBLIC_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    with open(archive_dir / f"{date_str}.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated: {archive_dir / f'{date_str}.html'}")


def generate_all():
    print("=== Generating HTML ===")
    generate_home()
    for date_str in get_all_dates():
        generate_archive_page(date_str)
    print("=== Done ===")


if __name__ == "__main__":
    generate_all()
