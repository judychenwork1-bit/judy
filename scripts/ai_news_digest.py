"""
Daily AI news digest — scrapes top X (Twitter) AI influencers via Nitter RSS
+ Hacker News, curates 10 items, emails to recipient.

Environment variables required:
    GMAIL_SENDER   - sender Gmail address
    GMAIL_PASSWORD - Gmail App Password (not login password)
    RECIPIENT_EMAIL - destination email
"""

import os
import smtplib
import sys
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TWITTER_ACCOUNTS = [
    "sama",           # Sam Altman - OpenAI CEO
    "karpathy",       # Andrej Karpathy
    "ylecun",         # Yann LeCun - Meta AI
    "demishassabis",  # Demis Hassabis - DeepMind CEO
    "fchollet",       # François Chollet - Keras
    "emollick",       # Ethan Mollick - AI applications
    "benedictevans",  # Benedict Evans - tech analyst
    "goodside",       # Riley Goodside - prompting
    "DrJimFan",       # Jim Fan - NVIDIA
    "elonmusk",       # Elon Musk - xAI
]

NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
    "https://nitter.net",
]

AI_KEYWORDS = [
    "ai", "llm", "gpt", "model", "agent", "chip", "gpu", "nvidia",
    "openai", "deepmind", "anthropic", "gemini", "claude",
    "算力", "大模型", "人工智能", "芯片", "inference", "training",
    "robot", "autonomous", "foundation model", "compute",
]

CUTOFF_HOURS = 24  # only items from last 24h


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def _is_recent(entry) -> bool:
    try:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published is None:
            return True
        ts = datetime(*published[:6], tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - ts < timedelta(hours=CUTOFF_HOURS)
    except Exception:
        return True


def _is_ai_relevant(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in AI_KEYWORDS)


def fetch_nitter(username: str) -> list[dict]:
    for instance in NITTER_INSTANCES:
        try:
            url = f"{instance}/{username}/rss"
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            if not feed.entries:
                continue
            results = []
            for e in feed.entries:
                if not _is_recent(e):
                    continue
                title = e.get("title", "")
                link = e.get("link", "")
                if not title or not link:
                    continue
                results.append({
                    "source": f"@{username}",
                    "title": title[:280],
                    "link": link,
                    "type": "twitter",
                })
            return results
        except Exception:
            continue
    return []


def fetch_hackernews() -> list[dict]:
    try:
        r = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
        )
        ids = r.json()[:60]
        items = []
        for story_id in ids:
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=5,
                ).json()
                title = s.get("title", "")
                url = s.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                age_h = (
                    (datetime.now(timezone.utc).timestamp() - s.get("time", 0)) / 3600
                )
                if age_h > CUTOFF_HOURS:
                    continue
                if _is_ai_relevant(title):
                    items.append({
                        "source": "Hacker News",
                        "title": title,
                        "link": url,
                        "type": "hn",
                        "score": s.get("score", 0),
                    })
            except Exception:
                continue
        items.sort(key=lambda x: x.get("score", 0), reverse=True)
        return items[:5]
    except Exception:
        return []


def fetch_google_news_rss() -> list[dict]:
    feeds = [
        ("Google News: AI", "https://news.google.com/rss/search?q=artificial+intelligence+OR+LLM+OR+%22AI+chip%22&hl=en-US&gl=US&ceid=US:en"),
        ("Google News: AI中文", "https://news.google.com/rss/search?q=%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD+OR+%E5%A4%A7%E6%A8%A1%E5%9E%8B+OR+%E7%AE%97%E5%8A%9B&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"),
    ]
    items = []
    for label, url in feeds:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:5]:
                if not _is_recent(e):
                    continue
                items.append({
                    "source": label,
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "type": "news",
                })
        except Exception:
            continue
    return items


# ---------------------------------------------------------------------------
# Curate top 10
# ---------------------------------------------------------------------------

def curate(all_items: list[dict], n: int = 10) -> list[dict]:
    seen_titles = set()
    curated = []
    # prioritize twitter, then hn, then news
    priority = {"twitter": 0, "hn": 1, "news": 2}
    all_items.sort(key=lambda x: priority.get(x.get("type", "news"), 3))
    for item in all_items:
        title = item.get("title", "").strip()
        if not title or title in seen_titles:
            continue
        if not _is_ai_relevant(title) and item.get("type") != "twitter":
            continue
        seen_titles.add(title)
        curated.append(item)
        if len(curated) >= n:
            break
    return curated


# ---------------------------------------------------------------------------
# Email builder
# ---------------------------------------------------------------------------

def build_html(items: list[dict]) -> str:
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    rows = ""
    for i, item in enumerate(items, 1):
        source = item["source"]
        title = item["title"]
        link = item["link"]
        rows += f"""
        <tr>
          <td style="padding:8px 4px;color:#888;font-size:13px;vertical-align:top">{i}</td>
          <td style="padding:8px 12px 8px 0">
            <span style="font-size:11px;background:#eef;color:#446;padding:2px 6px;border-radius:10px;margin-right:6px">{source}</span>
            <a href="{link}" style="color:#1a0dab;text-decoration:none;font-size:14px">{title}</a>
          </td>
        </tr>"""

    return f"""
<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;padding:20px">
  <h2 style="color:#222;border-bottom:2px solid #4a90d9;padding-bottom:8px">
    🤖 AI 每日精选 · {today}
  </h2>
  <p style="color:#555;font-size:13px">以下为过去24小时 AI 领域重要动态，精选自顶级研究者推文 + Hacker News + Google News</p>
  <table style="width:100%;border-collapse:collapse">{rows}
  </table>
  <hr style="margin-top:30px;border:none;border-top:1px solid #eee">
  <p style="color:#aaa;font-size:11px">
    投资有风险，本邮件仅供信息参考，不构成投资建议。<br>
    数据来源：X/Twitter · Hacker News · Google News
  </p>
</body></html>"""


def build_plain(items: list[dict]) -> str:
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    lines = [f"AI 每日精选 · {today}", "=" * 50, ""]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. [{item['source']}] {item['title']}")
        lines.append(f"   {item['link']}")
        lines.append("")
    lines.append("投资有风险，本邮件仅供信息参考，不构成投资建议。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def send_email(html: str, plain: str, subject: str, sender: str, password: str, recipient: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    sender = os.environ.get("GMAIL_SENDER", "")
    password = os.environ.get("GMAIL_PASSWORD", "")
    recipient = os.environ.get("RECIPIENT_EMAIL", "Judy.chen@morganstanley.com.cn")

    if not sender or not password:
        print("ERROR: Set GMAIL_SENDER and GMAIL_PASSWORD environment variables.", file=sys.stderr)
        sys.exit(1)

    print("Fetching Hacker News...")
    all_items = fetch_hackernews()

    print("Fetching Google News RSS...")
    all_items += fetch_google_news_rss()

    print("Fetching X / Nitter feeds...")
    for account in TWITTER_ACCOUNTS:
        tweets = fetch_nitter(account)
        all_items += tweets
        if tweets:
            print(f"  @{account}: {len(tweets)} items")

    top10 = curate(all_items, n=10)
    print(f"\nCurated {len(top10)} items.")

    if not top10:
        print("No items found — skipping email.")
        return

    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    subject = f"[AI日报] {today} 精选10条 · 算力/大模型/机器人"
    html = build_html(top10)
    plain = build_plain(top10)

    print(f"Sending email to {recipient}...")
    send_email(html, plain, subject, sender, password, recipient)
    print("Done.")


if __name__ == "__main__":
    main()
