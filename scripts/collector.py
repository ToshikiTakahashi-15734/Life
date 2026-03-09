#!/usr/bin/env python3
"""IT Trend Information Collector - 各ソースからトレンド情報を収集"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import feedparser
from bs4 import BeautifulSoup

JST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TODAY = datetime.now(JST).strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def fetch_hackernews():
    """Hacker News トップストーリーを取得"""
    print("  [HackerNews] Fetching...")
    items = []
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15
        )
        story_ids = resp.json()[:20]
        for sid in story_ids:
            r = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10
            )
            story = r.json()
            if story and story.get("title"):
                items.append({
                    "title": story["title"],
                    "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    "score": story.get("score", 0),
                    "comments": story.get("descendants", 0),
                    "source": "Hacker News",
                    "source_icon": "🟠",
                })
        print(f"  [HackerNews] {len(items)} articles fetched")
    except Exception as e:
        print(f"  [HackerNews] Error: {e}")
    return items


def fetch_hatena():
    """はてなブログ IT関連のホットエントリーを取得"""
    print("  [Hatena] Fetching...")
    items = []
    urls = [
        "https://b.hatena.ne.jp/hotentry/it.rss",
        "https://b.hatena.ne.jp/hotentry/technology.rss",
    ]
    seen = set()
    try:
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                if entry.link in seen:
                    continue
                seen.add(entry.link)
                items.append({
                    "title": entry.title,
                    "url": entry.link,
                    "score": 0,
                    "comments": 0,
                    "source": "はてなブログ",
                    "source_icon": "📘",
                })
        print(f"  [Hatena] {len(items)} articles fetched")
    except Exception as e:
        print(f"  [Hatena] Error: {e}")
    return items


def fetch_reddit():
    """Reddit の technology/programming サブレディットから取得"""
    print("  [Reddit] Fetching...")
    items = []
    subreddits = ["technology", "programming", "netsec"]
    try:
        for sub in subreddits:
            resp = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json?limit=10",
                headers={**HEADERS, "User-Agent": "ITTrendCollector/1.0"},
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            for post in data.get("data", {}).get("children", []):
                d = post["data"]
                if d.get("stickied"):
                    continue
                items.append({
                    "title": d["title"],
                    "url": d.get("url", f"https://reddit.com{d['permalink']}"),
                    "score": d.get("ups", 0),
                    "comments": d.get("num_comments", 0),
                    "source": f"Reddit r/{sub}",
                    "source_icon": "🔴",
                })
        print(f"  [Reddit] {len(items)} articles fetched")
    except Exception as e:
        print(f"  [Reddit] Error: {e}")
    return items


def fetch_aikido_security():
    """Aikido Security ブログから取得"""
    print("  [Aikido Security] Fetching...")
    items = []
    try:
        resp = requests.get(
            "https://www.aikido.dev/blog", headers=HEADERS, timeout=15
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a[href*='/blog/']")[:15]:
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not title or len(title) < 10 or title in ("Blog", "Read more"):
                    continue
                url = href if href.startswith("http") else f"https://www.aikido.dev{href}"
                uid = hashlib.md5(url.encode()).hexdigest()
                items.append({
                    "title": title,
                    "url": url,
                    "score": 0,
                    "comments": 0,
                    "source": "Aikido Security",
                    "source_icon": "🥋",
                })
        # 重複除去
        seen = set()
        unique = []
        for item in items:
            if item["title"] not in seen:
                seen.add(item["title"])
                unique.append(item)
        items = unique
        print(f"  [Aikido Security] {len(items)} articles fetched")
    except Exception as e:
        print(f"  [Aikido Security] Error: {e}")
    return items


def fetch_wiz_research():
    """Wiz Research ブログから取得"""
    print("  [Wiz Research] Fetching...")
    items = []
    try:
        resp = requests.get(
            "https://www.wiz.io/blog", headers=HEADERS, timeout=15
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a[href*='/blog/']")[:15]:
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not title or len(title) < 10:
                    continue
                url = href if href.startswith("http") else f"https://www.wiz.io{href}"
                items.append({
                    "title": title,
                    "url": url,
                    "score": 0,
                    "comments": 0,
                    "source": "Wiz Research",
                    "source_icon": "🔮",
                })
        seen = set()
        unique = []
        for item in items:
            if item["title"] not in seen:
                seen.add(item["title"])
                unique.append(item)
        items = unique
        print(f"  [Wiz Research] {len(items)} articles fetched")
    except Exception as e:
        print(f"  [Wiz Research] Error: {e}")
    return items


def collect_all():
    """全ソースから収集してJSONに保存"""
    print(f"=== IT Trend Collector - {TODAY} ===\n")

    all_items = []
    collectors = [
        fetch_hackernews,
        fetch_hatena,
        fetch_reddit,
        fetch_aikido_security,
        fetch_wiz_research,
    ]

    for collector in collectors:
        items = collector()
        all_items.extend(items)
        print()

    # 日付ディレクトリにJSON保存
    date_dir = DATA_DIR / TODAY
    date_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "date": TODAY,
        "collected_at": datetime.now(JST).isoformat(),
        "total_count": len(all_items),
        "articles": all_items,
    }

    output_path = date_dir / "trends.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"=== Complete: {len(all_items)} articles saved to {output_path} ===")
    return output


if __name__ == "__main__":
    collect_all()
