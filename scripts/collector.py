#!/usr/bin/env python3
"""IT Trend Information Collector - 各ソースからトレンド情報を収集"""

import json
import os
import re
import sys
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import feedparser
from bs4 import BeautifulSoup

from urllib.parse import urlparse

JST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TODAY = datetime.now(JST).strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# --- Security Filters ---

ALLOWED_SCHEMES = {"http", "https"}

DANGEROUS_EXTENSIONS = {
    ".exe", ".msi", ".bat", ".cmd", ".scr", ".pif", ".com", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".ps1", ".psm1", ".reg", ".inf", ".hta",
    ".cpl", ".msc", ".jar", ".apk", ".dmg", ".iso", ".img", ".torrent",
}

MALICIOUS_URL_PATTERNS = [
    re.compile(r"bit\.ly/", re.IGNORECASE),
    re.compile(r"tinyurl\.com/", re.IGNORECASE),
    re.compile(r"t\.co/", re.IGNORECASE),
    re.compile(r"adf\.ly/", re.IGNORECASE),
    re.compile(r"goo\.gl/", re.IGNORECASE),
]

XSS_PATTERNS = [
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"<\s*object", re.IGNORECASE),
    re.compile(r"<\s*embed", re.IGNORECASE),
    re.compile(r"<\s*form", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"url\s*\(\s*['\"]?\s*javascript", re.IGNORECASE),
]

CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060\ufeff]")


def is_safe_url(url):
    """URLが安全かチェック"""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # スキームチェック
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False

    # ホスト名が空
    if not parsed.hostname:
        return False

    # IPアドレス直打ち (プライベートIP) のブロック
    hostname = parsed.hostname.lower()
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", hostname):
        parts = hostname.split(".")
        try:
            first = int(parts[0])
            if first == 10 or first == 127:
                return False
            if first == 172 and 16 <= int(parts[1]) <= 31:
                return False
            if first == 192 and int(parts[1]) == 168:
                return False
            if first == 0:
                return False
        except (ValueError, IndexError):
            return False

    # 危険なファイル拡張子の直リンク
    path_lower = parsed.path.lower()
    for ext in DANGEROUS_EXTENSIONS:
        if path_lower.endswith(ext):
            return False

    # 短縮URL (リダイレクト先が不明)
    for pattern in MALICIOUS_URL_PATTERNS:
        if pattern.search(url):
            return False

    return True


def sanitize_text(text):
    """テキストからXSS・制御文字・不審な文字列を除去"""
    if not text or not isinstance(text, str):
        return ""

    # 制御文字・不可視文字の除去
    text = CONTROL_CHAR_RE.sub("", text)

    # XSSパターンの除去
    for pattern in XSS_PATTERNS:
        text = pattern.sub("[removed]", text)

    # HTMLタグを全除去 (プレーンテキストのみ残す)
    text = re.sub(r"<[^>]+>", "", text)

    return text.strip()


def sanitize_article(article):
    """記事データ全体をサニタイズ。安全でなければNoneを返す"""
    url = article.get("url", "")
    if not is_safe_url(url):
        print(f"    [BLOCKED] Unsafe URL: {url[:80]}")
        return None

    article["title"] = sanitize_text(article.get("title", ""))
    article["summary"] = sanitize_text(article.get("summary", ""))

    # タイトルが空または極端に短い場合は除外
    if not article["title"] or len(article["title"]) < 3:
        print(f"    [BLOCKED] Empty/invalid title for: {url[:80]}")
        return None

    return article


def summarize_from_url(url):
    """URLからページのmeta descriptionやog:descriptionを取得して備考にする"""
    if not is_safe_url(url):
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        # og:description > meta description > 最初のpタグ
        og = soup.find("meta", property="og:description")
        if og and og.get("content"):
            return og["content"].strip()[:120]
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()[:120]
        p = soup.find("p")
        if p:
            text = p.get_text(strip=True)
            if len(text) > 15:
                return text[:120]
    except Exception:
        pass
    return ""


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
                url = story.get("url", f"https://news.ycombinator.com/item?id={sid}")
                summary = summarize_from_url(url)
                items.append({
                    "title": story["title"],
                    "url": url,
                    "summary": summary,
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
                summary = getattr(entry, "summary", "") or ""
                summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)[:120] if summary else ""
                items.append({
                    "title": entry.title,
                    "url": entry.link,
                    "summary": summary,
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
                summary = (d.get("selftext") or "")[:120]
                if not summary:
                    summary = d.get("link_flair_text") or ""
                items.append({
                    "title": d["title"],
                    "url": d.get("url", f"https://reddit.com{d['permalink']}"),
                    "summary": summary,
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
                # 親要素からdescription的なテキストを探す
                parent = a.find_parent()
                summary = ""
                if parent:
                    p = parent.find_next_sibling("p") or parent.find("p")
                    if p:
                        summary = p.get_text(strip=True)[:120]
                items.append({
                    "title": title,
                    "url": url,
                    "summary": summary,
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
                parent = a.find_parent()
                summary = ""
                if parent:
                    p = parent.find_next_sibling("p") or parent.find("p")
                    if p:
                        summary = p.get_text(strip=True)[:120]
                items.append({
                    "title": title,
                    "url": url,
                    "summary": summary,
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

    blocked_count = 0
    for collector in collectors:
        items = collector()
        for item in items:
            safe = sanitize_article(item)
            if safe:
                all_items.append(safe)
            else:
                blocked_count += 1
        print()

    if blocked_count:
        print(f"  [Security] {blocked_count} articles blocked\n")

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
