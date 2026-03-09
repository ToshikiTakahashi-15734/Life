#!/usr/bin/env python3
"""JSON データから静的HTMLページを直接生成"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape

JST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = BASE_DIR / "public"


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


def render_article_card(a):
    title = escape(a["title"])
    url = escape(a["url"])
    source = escape(a["source"])
    icon = a.get("source_icon", "")
    score = a.get("score", 0)
    comments = a.get("comments", 0)

    meta_parts = []
    if score:
        meta_parts.append(f'<span class="score">&#9650; {score}</span>')
    if comments:
        meta_parts.append(f'<span class="comments">&#128172; {comments}</span>')
    meta_html = " ".join(meta_parts)

    return f'''<article class="card">
  <a href="{url}" target="_blank" rel="noopener">{title}</a>
  <div class="card-meta">
    <span class="source">{icon} {source}</span>
    {meta_html}
  </div>
</article>'''


def css():
    return '''<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:#0f1117;color:#e0e0e0;line-height:1.6}
header{background:linear-gradient(135deg,#1a1c2e,#2d1b4e);padding:24px 32px;
  border-bottom:1px solid #2a2d3e}
header h1{font-size:1.6rem;color:#fff}
header p{color:#9ca3af;font-size:.85rem;margin-top:4px}
.container{max-width:1200px;margin:0 auto;padding:24px}
.source-section{margin-bottom:32px}
.source-title{font-size:1.15rem;color:#c4b5fd;margin-bottom:12px;
  padding-bottom:6px;border-bottom:1px solid #2a2d3e;display:flex;align-items:center;gap:8px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}
.card{background:#1a1c2e;border:1px solid #2a2d3e;border-radius:8px;padding:14px 16px;
  transition:border-color .2s,transform .15s}
.card:hover{border-color:#7c3aed;transform:translateY(-2px)}
.card a{color:#e2e8f0;text-decoration:none;font-size:.93rem;font-weight:500;
  display:block;margin-bottom:6px}
.card a:hover{color:#a78bfa}
.card-meta{display:flex;gap:12px;font-size:.78rem;color:#6b7280}
.card-meta .score{color:#f59e0b}
.card-meta .comments{color:#60a5fa}
.card-meta .source{color:#9ca3af}
nav.archives{margin-top:32px;padding:20px;background:#1a1c2e;border-radius:8px;
  border:1px solid #2a2d3e}
nav.archives h2{font-size:1rem;color:#c4b5fd;margin-bottom:10px}
nav.archives a{color:#60a5fa;text-decoration:none;margin-right:14px;font-size:.88rem}
nav.archives a:hover{text-decoration:underline}
.empty{text-align:center;padding:60px 20px;color:#6b7280}
.back-link{display:inline-block;margin-bottom:16px;color:#60a5fa;text-decoration:none;font-size:.9rem}
.back-link:hover{text-decoration:underline}
.stats{display:flex;gap:20px;margin-top:8px}
.stats span{background:#1e2033;padding:4px 12px;border-radius:20px;font-size:.8rem;color:#9ca3af}
</style>'''


def generate_home():
    today = datetime.now(JST).strftime("%Y-%m-%d")
    data = load_trends(today)
    dates = get_all_dates()
    generated = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")

    body_content = ""
    if data and data["articles"]:
        sources = group_by_source(data["articles"])
        for src_name, src_data in sources.items():
            cards = "\n".join(render_article_card(a) for a in src_data["articles"])
            body_content += f'''<section class="source-section">
  <h2 class="source-title">{src_data["icon"]} {escape(src_name)}</h2>
  <div class="cards">{cards}</div>
</section>\n'''
        stats = f'''<div class="stats">
  <span>Total: {data["total_count"]} articles</span>
  <span>Sources: {len(sources)}</span>
</div>'''
    else:
        body_content = '<div class="empty"><p>No data for today yet.</p><p>Run <code>python scripts/run.py</code> to collect trends.</p></div>'
        stats = ""

    archive_links = "\n".join(
        f'<a href="archive/{d}.html">{d}</a>' for d in dates
    )
    archive_section = ""
    if dates:
        archive_section = f'''<nav class="archives">
  <h2>Archive</h2>
  <div>{archive_links}</div>
</nav>'''

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
  <p>{today} | Updated: {generated}</p>
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
        cards = "\n".join(render_article_card(a) for a in src_data["articles"])
        body_content += f'''<section class="source-section">
  <h2 class="source-title">{src_data["icon"]} {escape(src_name)}</h2>
  <div class="cards">{cards}</div>
</section>\n'''

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IT Trends - {date_str}</title>
{css()}
</head>
<body>
<header>
  <h1>IT Trend Dashboard</h1>
  <p>{date_str} | {data["total_count"]} articles</p>
</header>
<main class="container">
<a href="../index.html" class="back-link">&larr; Back to Home</a>
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
