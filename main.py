#!/usr/bin/env python3
"""
World Briefing Bot
4 separate messages: Football, Trends, Geopolitics, AI News
Schedule: Every 6 hours + 6 AM Nepal time
"""

import requests
from bs4 import BeautifulSoup
import time
import os
import re
from datetime import datetime, timezone, timedelta

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

NEPAL_TZ = timezone(timedelta(hours=5, minutes=45))

def nepal_now(): return datetime.now(NEPAL_TZ)
def now_str():   return nepal_now().strftime("%d %b %Y, %I:%M %p NST")
def log(msg):    print(f"[{nepal_now().strftime('%H:%M:%S')}] {msg}", flush=True)

def send_telegram(message):
    try:
        if len(message) > 4096:
            message = message[:4090] + "..."
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
        log("Sent!" if r.status_code == 200 else f"TG error: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"TG error: {e}")

def get_field(tag, content):
    m = re.search(rf'<{tag}[^>]*>\s*(.*?)\s*</{tag}>', content, re.DOTALL)
    if m:
        val = m.group(1).strip()
        val = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', val, flags=re.DOTALL)
        return BeautifulSoup(val, "html.parser").get_text(strip=True)
    return ""

def fetch_rss(url, keywords=[], max_items=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSS Reader)",
        "Accept": "application/rss+xml, text/xml, */*"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        text = resp.content.decode("utf-8", errors="replace")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        items = []
        for block in re.findall(r'<item[^>]*>(.*?)</item>', text, re.DOTALL):
            title = get_field("title", block)
            link  = get_field("link", block)
            desc  = get_field("description", block)[:200]
            if not title:
                continue
            combined = (title + " " + desc).lower()
            if keywords and not any(k.lower() in combined for k in keywords):
                continue
            items.append({"title": title, "link": link, "desc": desc})
            if len(items) >= max_items:
                break
        return items
    except Exception as e:
        log(f"RSS fetch error ({url[:40]}): {e}")
        return []

# ── Fetchers ─────────────────────────────────────────────────────────────

FOOTBALL_KW = ["premier league", "champions league", "la liga", "barcelona",
               "real madrid", "liverpool", "arsenal", "manchester", "chelsea",
               "tottenham", "goal", "match", "score", "win", "defeat", "draw"]

def fetch_football():
    sources = [
        ("https://feeds.bbci.co.uk/sport/football/rss.xml",        FOOTBALL_KW),
        ("https://www.skysports.com/rss/12040",                     FOOTBALL_KW),
        ("https://www.goal.com/feeds/en/news",                      FOOTBALL_KW),
        ("https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml", []),
    ]
    items = []
    seen  = set()
    for url, kw in sources:
        for item in fetch_rss(url, kw, max_items=8):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key)
                items.append(item)
    return items[:15]

def fetch_trends():
    sources = [
        ("https://trends.google.com/trending/rss?geo=US", []),
        ("https://trends.google.com/trending/rss?geo=NP", []),
        ("https://trends.google.com/trending/rss?geo=GB", []),
    ]
    items = []
    seen_titles = set()
    seen_words  = set()  # catch near-duplicates like "weather today" vs "today weather"
    for url, kw in sources:
        for item in fetch_rss(url, kw, max_items=15):
            title = item["title"].strip()
            # Skip junk: single char, very short, or pure numbers
            if len(title) < 4 or title.isdigit():
                continue
            key   = title.lower()
            words = frozenset(key.split())
            # Skip exact duplicates
            if key in seen_titles:
                continue
            # Skip near-duplicates (same words different order)
            if words in seen_words:
                continue
            seen_titles.add(key)
            seen_words.add(words)
            items.append(item)
    return items[:15]

GEO_KW = ["war", "conflict", "diplomacy", "sanctions", "military", "treaty",
           "president", "prime minister", "nato", "united nations", "crisis",
           "ceasefire", "attack", "invasion", "nuclear", "election", "protest",
           "summit", "agreement", "tension", "troops", "alliance"]

def fetch_geo():
    sources = [
        ("https://feeds.reuters.com/reuters/worldNews",     GEO_KW),
        ("https://www.aljazeera.com/xml/rss/all.xml",       GEO_KW),
        ("https://rss.nytimes.com/services/xml/rss/nyt/World.xml", GEO_KW),
        ("https://feeds.bbci.co.uk/news/world/rss.xml",    GEO_KW),
    ]
    items = []
    seen  = set()
    for url, kw in sources:
        for item in fetch_rss(url, kw, max_items=6):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key)
                items.append(item)
    return items[:15]

AI_KW = ["ai", "artificial intelligence", "llm", "gpt", "openai", "anthropic",
         "gemini", "claude", "machine learning", "deep learning", "neural",
         "robot", "automation", "chatbot", "model", "nvidia", "chip", "agi"]

def fetch_ai():
    sources = [
        ("https://techcrunch.com/category/artificial-intelligence/feed/", AI_KW),
        ("https://venturebeat.com/category/ai/feed/",                      AI_KW),
        ("https://www.wired.com/feed/category/artificial-intelligence/latest/rss", AI_KW),
        ("https://feeds.bbci.co.uk/news/technology/rss.xml",               AI_KW),
    ]
    items = []
    seen  = set()
    for url, kw in sources:
        for item in fetch_rss(url, kw, max_items=6):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key)
                items.append(item)
    return items[:15]

# ── Message builders ──────────────────────────────────────────────────────

def build_football(items):
    lines = [
        "⚽ <b>FOOTBALL — LATEST SCORES &amp; NEWS</b>",
        f"🕐 <i>{now_str()}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🏆 Premier League | Champions League | La Liga",
        ""
    ]
    if not items:
        lines.append("⚠️ No football news available right now.")
    else:
        for item in items:
            lines.append(f"🔸 <b>{item['title']}</b>")
            if item.get("desc") and item["desc"].lower() != item["title"].lower():
                lines.append(f"    <i>{item['desc'][:180]}</i>")
            if item.get("link"):
                lines.append(f"    🔗 <a href='{item['link']}'>Full story</a>")
            lines.append("")
    return "\n".join(lines)

def build_trends(items):
    lines = [
        "🔥 <b>LATEST TRENDS</b>",
        f"🕐 <i>{now_str()}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📊 Trending globally right now",
        ""
    ]
    if not items:
        lines.append("⚠️ No trending topics available right now.")
    else:
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. 🔺 <b>{item['title']}</b>")
            if item.get("desc") and item["desc"].lower() != item["title"].lower():
                lines.append(f"    <i>{item['desc'][:150]}</i>")
            if item.get("link"):
                lines.append(f"    🔗 <a href='{item['link']}'>Explore</a>")
            lines.append("")
    lines.append("📡 <i>Source: Google Trends — US | UK | NP</i>")
    return "\n".join(lines)

def build_geo(items):
    lines = [
        "🌍 <b>GEOPOLITICS UPDATE</b>",
        f"🕐 <i>{now_str()}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🗺 World affairs, conflicts &amp; diplomacy",
        ""
    ]
    if not items:
        lines.append("⚠️ No geopolitical news available right now.")
    else:
        for item in items:
            lines.append(f"🔹 <b>{item['title']}</b>")
            if item.get("desc") and item["desc"].lower() != item["title"].lower():
                lines.append(f"    <i>{item['desc'][:180]}</i>")
            if item.get("link"):
                lines.append(f"    🔗 <a href='{item['link']}'>Read more</a>")
            lines.append("")
    lines.append("📡 <i>Sources: Reuters | Al Jazeera | BBC | NYT</i>")
    return "\n".join(lines)

def build_ai(items):
    lines = [
        "🤖 <b>AI NEWS</b>",
        f"🕐 <i>{now_str()}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "💡 Latest in Artificial Intelligence",
        ""
    ]
    if not items:
        lines.append("⚠️ No AI news available right now.")
    else:
        for item in items:
            lines.append(f"⚡ <b>{item['title']}</b>")
            if item.get("desc") and item["desc"].lower() != item["title"].lower():
                lines.append(f"    <i>{item['desc'][:180]}</i>")
            if item.get("link"):
                lines.append(f"    🔗 <a href='{item['link']}'>Read more</a>")
            lines.append("")
    lines.append("📡 <i>Sources: TechCrunch | VentureBeat | Wired | BBC Tech</i>")
    return "\n".join(lines)

# ── Main scheduler ────────────────────────────────────────────────────────

def send_briefing():
    log("━━━ Sending briefing ━━━")

    # Header
    send_telegram(
        f"🌐 <b>WORLD BRIEFING</b>\n"
        f"🕐 <i>{now_str()}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Today's update in 4 sections:\n"
        f"    ⚽ Football\n"
        f"    🔥 Trends\n"
        f"    🌍 Geopolitics\n"
        f"    🤖 AI News"
    )
    time.sleep(2)

    try:
        send_telegram(build_football(fetch_football()))
        log("Football sent")
    except Exception as e:
        log(f"Football error: {e}")
    time.sleep(2)

    try:
        send_telegram(build_trends(fetch_trends()))
        log("Trends sent")
    except Exception as e:
        log(f"Trends error: {e}")
    time.sleep(2)

    try:
        send_telegram(build_geo(fetch_geo()))
        log("Geo sent")
    except Exception as e:
        log(f"Geo error: {e}")
    time.sleep(2)

    try:
        send_telegram(build_ai(fetch_ai()))
        log("AI sent")
    except Exception as e:
        log(f"AI error: {e}")

    log("━━━ Briefing complete ━━━")

def should_send(last_sent):
    now = nepal_now()
    if last_sent is None:
        return True
    # 6 AM Nepal time
    if now.hour == 6 and now.minute < 2:
        if last_sent.date() < now.date():
            return True
    # Every 6 hours
    if (now - last_sent).total_seconds() >= 6 * 3600:
        return True
    return False

def run_agent():
    if not TOKEN or not CHAT_ID:
        log("ERROR: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return

    log("World Briefing Bot started!")
    send_telegram(
        "🌐 <b>World Briefing Bot — Online!</b>\n\n"
        "Updates every 6 hours + daily at 6:00 AM NST\n\n"
        "    ⚽ Football scores &amp; news\n"
        "    🔥 Latest global trends\n"
        "    🌍 Geopolitics &amp; world affairs\n"
        "    🤖 AI &amp; tech news\n\n"
        "<i>Sending first briefing now...</i>"
    )
    time.sleep(3)

    send_briefing()
    last_sent = nepal_now()

    while True:
        time.sleep(60)
        if should_send(last_sent):
            send_briefing()
            last_sent = nepal_now()

if __name__ == "__main__":
    run_agent()
