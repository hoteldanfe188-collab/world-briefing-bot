#!/usr/bin/env python3
"""
World Briefing Bot - 4 separate messages
Football | Trends | Geopolitics | AI News
"""

import requests
from bs4 import BeautifulSoup
import time
import os
import re
from datetime import datetime, timezone, timedelta

TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID", "")
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

def fetch_rss(url, keywords=[], max_items=15):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        text = resp.content.decode("utf-8", errors="replace")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        items = []
        for block in re.findall(r'<item[^>]*>(.*?)</item>', text, re.DOTALL):
            title = get_field("title", block)
            link  = get_field("link", block)
            desc  = get_field("description", block)
            if not title:
                continue
            desc = re.sub(r'\s+', ' ', desc).strip()[:250]
            combined = (title + " " + desc).lower()
            if keywords and not any(k.lower() in combined for k in keywords):
                continue
            items.append({"title": title, "link": link, "desc": desc})
            if len(items) >= max_items:
                break
        log(f"  RSS OK: {url[:50]} → {len(items)} items")
        return items
    except Exception as e:
        log(f"  RSS FAIL: {url[:50]} → {e}")
        return []

# ── FOOTBALL ─────────────────────────────────────────────────────────────
FOOTBALL_KW = ["premier league", "champions league", "la liga", "barcelona",
               "real madrid", "liverpool", "arsenal", "manchester", "chelsea",
               "tottenham", "goal", "score", "match", "win", "defeat", "draw",
               "epl", "ucl", "transfer", "injury", "result", "fixture"]

def fetch_football():
    sources = [
        "https://www.theguardian.com/football/rss",
        "https://www.theguardian.com/football/premierleague/rss",
        "https://www.theguardian.com/football/championsleague/rss",
        "https://www.theguardian.com/football/laliga/rss",
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
    ]
    items = []
    seen = set()
    for url in sources:
        for item in fetch_rss(url, FOOTBALL_KW, max_items=8):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key)
                items.append(item)
    return items[:15]

# ── TRENDS ───────────────────────────────────────────────────────────────
def fetch_trends():
    sources = [
        "https://trends.google.com/trending/rss?geo=US",
        "https://trends.google.com/trending/rss?geo=GB",
        "https://trends.google.com/trending/rss?geo=NP",
    ]
    items = []
    seen = set()
    for url in sources:
        for item in fetch_rss(url, [], max_items=10):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key)
                items.append(item)
    return items[:15]

# ── GEOPOLITICS ──────────────────────────────────────────────────────────
GEO_KW = ["war", "conflict", "diplomacy", "sanction", "military", "treaty",
           "president", "prime minister", "nato", "united nations", "crisis",
           "ceasefire", "attack", "invasion", "nuclear", "protest", "summit",
           "tension", "troops", "alliance", "government", "minister", "peace",
           "election", "vote", "policy", "trade", "tariff", "china", "russia",
           "ukraine", "israel", "india", "pakistan", "nepal", "us ", "eu "]

def fetch_geo():
    sources = [
        "https://www.theguardian.com/world/rss",
        "https://www.theguardian.com/world/ukraine/rss",
        "https://www.theguardian.com/world/middleeast/rss",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
    ]
    items = []
    seen = set()
    for url in sources:
        for item in fetch_rss(url, GEO_KW, max_items=6):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key)
                items.append(item)
    return items[:15]

# ── AI NEWS ──────────────────────────────────────────────────────────────
AI_KW = ["ai", "artificial intelligence", "llm", "gpt", "openai", "anthropic",
         "gemini", "claude", "machine learning", "deep learning", "neural",
         "chatbot", "language model", "nvidia", "automation", "robot", "agi",
         "generative", "deepmind", "meta ai", "copilot", "tech", "chip"]

def fetch_ai():
    sources = [
        "https://www.theguardian.com/technology/artificialintelligenceai/rss",
        "https://www.theguardian.com/technology/rss",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://techcrunch.com/feed/",
    ]
    items = []
    seen = set()
    for url in sources:
        for item in fetch_rss(url, AI_KW, max_items=6):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key)
                items.append(item)
    return items[:15]

# ── Message builders ──────────────────────────────────────────────────────

def build_football(items):
    lines = [
        "⚽ <b>FOOTBALL — SCORES &amp; NEWS</b>",
        f"🕐 <i>{now_str()}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━", ""
    ]
    if not items:
        lines.append("⚠️ No football news available right now.")
    else:
        for item in items:
            lines.append(f"🔸 <b>{item['title']}</b>")
            if item['desc'] and item['desc'].lower() != item['title'].lower():
                lines.append(f"    <i>{item['desc'][:200]}</i>")
            if item['link']:
                lines.append(f"    🔗 <a href='{item['link']}'>Full story</a>")
            lines.append("")
    lines.append("📡 <i>Premier League | Champions League | La Liga</i>")
    return "\n".join(lines)

def build_trends(items):
    lines = [
        "🔥 <b>LATEST TRENDS</b>",
        f"🕐 <i>{now_str()}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━", ""
    ]
    if not items:
        lines.append("⚠️ No trending topics right now.")
    else:
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. 🔺 <b>{item['title']}</b>")
            if item['link']:
                lines.append(f"    🔗 <a href='{item['link']}'>Explore →</a>")
            lines.append("")
    lines.append("📡 <i>Google Trends: US | UK | Nepal</i>")
    return "\n".join(lines)

def build_geo(items):
    lines = [
        "🌍 <b>GEOPOLITICS</b>",
        f"🕐 <i>{now_str()}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━", ""
    ]
    if not items:
        lines.append("⚠️ No geopolitical news right now.")
    else:
        for item in items:
            lines.append(f"🔹 <b>{item['title']}</b>")
            if item['desc'] and item['desc'].lower() != item['title'].lower():
                lines.append(f"    <i>{item['desc'][:200]}</i>")
            if item['link']:
                lines.append(f"    🔗 <a href='{item['link']}'>Read more</a>")
            lines.append("")
    lines.append("📡 <i>Sources: The Guardian | BBC World</i>")
    return "\n".join(lines)

def build_ai(items):
    lines = [
        "🤖 <b>AI NEWS</b>",
        f"🕐 <i>{now_str()}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━", ""
    ]
    if not items:
        lines.append("⚠️ No AI news right now.")
    else:
        for item in items:
            lines.append(f"⚡ <b>{item['title']}</b>")
            if item['desc'] and item['desc'].lower() != item['title'].lower():
                lines.append(f"    <i>{item['desc'][:200]}</i>")
            if item['link']:
                lines.append(f"    🔗 <a href='{item['link']}'>Read more</a>")
            lines.append("")
    lines.append("📡 <i>Sources: The Guardian | BBC Tech | TechCrunch</i>")
    return "\n".join(lines)

# ── Scheduler ─────────────────────────────────────────────────────────────

def send_briefing():
    log("=== Sending briefing ===")

    try:
        items = fetch_football()
        log(f"Football: {len(items)} stories")
        send_telegram(build_football(items))
    except Exception as e:
        log(f"Football error: {e}")
    time.sleep(2)

    try:
        items = fetch_trends()
        log(f"Trends: {len(items)} topics")
        send_telegram(build_trends(items))
    except Exception as e:
        log(f"Trends error: {e}")
    time.sleep(2)

    try:
        items = fetch_geo()
        log(f"Geo: {len(items)} stories")
        send_telegram(build_geo(items))
    except Exception as e:
        log(f"Geo error: {e}")
    time.sleep(2)

    try:
        items = fetch_ai()
        log(f"AI: {len(items)} stories")
        send_telegram(build_ai(items))
    except Exception as e:
        log(f"AI error: {e}")

    log("=== Briefing complete ===")

def should_send(last_sent):
    now = nepal_now()
    if last_sent is None:
        return True
    if now.hour == 6 and now.minute < 2 and last_sent.date() < now.date():
        return True
    if (now - last_sent).total_seconds() >= 6 * 3600:
        return True
    return False

def run_agent():
    if not TOKEN or not CHAT_ID:
        log("ERROR: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return
    log("World Briefing Bot started!")
    send_briefing()
    last_sent = nepal_now()
    while True:
        time.sleep(60)
        if should_send(last_sent):
            send_briefing()
            last_sent = nepal_now()

if __name__ == "__main__":
    run_agent()
