# Life - IT Trend Dashboard

毎日のIT/セキュリティトレンド情報を複数ソースから自動収集し、HTMLダッシュボードとして表示するツール。

## プロジェクト構成

```
Life/
├── scripts/
│   ├── collector.py      # データ収集（各ソースからAPI/RSS/スクレイピング）
│   ├── generate_html.py  # JSON → 静的HTML生成
│   └── run.py            # メインエントリポイント（収集 → HTML生成 → ブラウザ表示）
├── data/
│   └── YYYY-MM-DD/
│       └── trends.json   # 日別の収集データ
├── public/
│   ├── index.html        # 当日のダッシュボード
│   └── archive/
│       └── YYYY-MM-DD.html  # 過去のアーカイブページ
├── templates/            # （未使用）
└── requirements.txt      # Python依存パッケージ
```

## データソース（14箇所）

### 海外テック全般
| Source | 取得方法 | 内容 |
|--------|----------|------|
| Hacker News | Firebase API | テック全般トップストーリー（HN討論+原文リンク） |
| Ars Technica | RSS | 技術解説・法規制・ハードウェア |
| TLDR Newsletter | RSS (Tech/WebDev/InfoSec) | 毎日の技術ニュース要約 |

### セキュリティ特化
| Source | 取得方法 | 内容 |
|--------|----------|------|
| The Hacker News (THN) | RSS | 最新の脆弱性・サイバー攻撃情報 |
| BleepingComputer | RSS | ランサムウェア・攻撃手口・実務的対策 |
| JVN | RSS | 国内向け脆弱性情報（IPA/JPCERT/CC運営） |
| Krebs on Security | RSS | 調査報道・犯罪組織の内実 |
| Aikido Security | HTMLスクレイピング | セキュリティブログ |
| Wiz Research | HTMLスクレイピング | クラウドセキュリティリサーチ |

### 国内エンジニア向け
| Source | 取得方法 | 内容 |
|--------|----------|------|
| はてなブックマーク | RSS (feedparser) | IT/テクノロジーホットエントリー |
| Qiita | REST API v2 | 日本語テック記事トレンド |
| Zenn | JSON API | 日本語テック記事デイリートレンド |

### その他
| Source | 取得方法 | 内容 |
|--------|----------|------|
| Reddit | JSON API (old.reddit.com) | r/technology, r/programming, r/netsec |
| JavaScript Weekly | RSS (feedparser) | JSニュースレター（月曜のみ） |

## 実行方法

```bash
# 全工程（収集 → HTML生成 → ブラウザ表示）
python3 scripts/run.py

# 個別実行
python3 scripts/collector.py      # 収集のみ
python3 scripts/generate_html.py  # HTML生成のみ
```

Claude Code からは `/trends` スキルで実行可能。

## セキュリティ設計

collector.py には以下のセキュリティ対策が実装済み。変更時はこれらを維持すること：

- **URL検証** (`is_safe_url`): スキーム制限、プライベートIP/SSRF防止、危険な拡張子・短縮URLブロック
- **XSSサニタイズ** (`sanitize_text`): script/iframe/event handler等のパターン除去、制御文字除去
- **記事サニタイズ** (`sanitize_article`): URL安全性 + テキストサニタイズの統合チェック
- **安全なHTTPリクエスト** (`_safe_get`): レスポンスサイズ5MB制限、ストリーム読み込み
- **リダイレクト先検証** (`_safe_get_with_redirect`): リダイレクト先URLも安全性チェック
- **HTMLエスケープ**: generate_html.py で全出力を `html.escape()` 処理

## 重複排除

過去7日分の `trends.json` からURLを抽出し、既出記事を自動除外する。

## 依存パッケージ

```
requests, beautifulsoup4, feedparser
```

## コミット規約

データ更新時: `Daily trends: YYYY-MM-DD`
