#!/usr/bin/env python3
"""
World Briefing Bot
4 separate messages: Football | Trends | Geopolitics | AI News
Schedule: Every 6 hours + 6 AM Nepal time
"""

import requests
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

def send_message(text):
    try:
        if len(text) > 4096:
            text = text[:4090] + "..."
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id":                  CHAT_ID,
                "text":                     text,
                "parse_mode":               "HTML",
                "disable_web_page_preview": True
            },
            timeout=10
        )
        log("Sent!" if r.status_code == 200 else f"TG error: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"TG error: {e}")

def clean(val):
    """Strip ALL HTML, decode entities, escape leftover < > for Telegram"""
    val = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', val, flags=re.DOTALL)
    val = re.sub(r'<[^>]+>', ' ', val)
    val = val.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    val = val.replace('&quot;', '"').replace('&apos;', "'").replace('&nbsp;', ' ')
    val = re.sub(r'&#?[a-zA-Z0-9]+;', ' ', val)
    val = re.sub(r'\s+', ' ', val).strip()
    # Re-escape so Telegram HTML parser won't choke on stray < >
    val = val.replace('<', '&lt;').replace('>', '&gt;')
    return val

def get_field(tag, block):
    m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', block, re.DOTALL)
    return clean(m.group(1)) if m else ""

def fetch_rss(url, keywords=None, max_items=15, is_trends=False):
    try:
        headers = {
            "User-Agent":      "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        text = resp.content.decode("utf-8", errors="replace")
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        items = []
        for block in re.findall(r'<item[^>]*>(.*?)</item>', text, re.DOTALL):
            title = get_field("title", block)
            link  = get_field("link",  block)
            desc  = get_field("description", block)[:250]
            if not title:
                continue

            news_titles = []
            if is_trends:
                raw = re.findall(r'<ht:news_item_title>(.*?)</ht:news_item_title>', block, re.DOTALL)
                news_titles = [clean(t) for t in raw[:3]]

            if keywords:
                combined = (title + " " + desc).lower()
                if not any(k.lower() in combined for k in keywords):
                    continue

            items.append({"title": title, "link": link, "desc": desc, "news": news_titles})
            if len(items) >= max_items:
                break

        log(f"  RSS OK {url[:55]} -> {len(items)} items")
        return items
    except Exception as e:
        log(f"  RSS FAIL {url[:55]} -> {e}")
        return []

# ── Fetchers ──────────────────────────────────────────────────────────────

FOOTBALL_KW = ["premier league","champions league","la liga","barcelona","real madrid",
               "liverpool","arsenal","manchester","chelsea","tottenham","goal","score",
               "match","win","defeat","draw","epl","ucl","transfer","injury","result","fixture"]

def fetch_football():
    sources = [
        "https://www.theguardian.com/football/rss",
        "https://www.theguardian.com/football/premierleague/rss",
        "https://www.theguardian.com/football/championsleague/rss",
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
    ]
    items, seen = [], set()
    for url in sources:
        for item in fetch_rss(url, FOOTBALL_KW, max_items=8):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key); items.append(item)
    return items[:15]

def fetch_trends():
    sources = [
        "https://trends.google.com/trending/rss?geo=US",
        "https://trends.google.com/trending/rss?geo=GB",
        "https://trends.google.com/trending/rss?geo=NP",
    ]
    items, seen = [], set()
    for url in sources:
        for item in fetch_rss(url, max_items=10, is_trends=True):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key); items.append(item)
    return items[:15]

GEO_KW = ["war","conflict","diplomacy","sanction","military","treaty","president",
          "prime minister","nato","united nations","crisis","ceasefire","attack",
          "invasion","nuclear","protest","summit","tension","troops","alliance",
          "government","minister","peace","election","policy","trade","tariff",
          "china","russia","ukraine","israel","india","pakistan","nepal","iran"]

def fetch_geo():
    sources = [
        "https://www.theguardian.com/world/rss",
        "https://www.theguardian.com/world/ukraine/rss",
        "https://www.theguardian.com/world/middleeast/rss",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
    ]
    items, seen = [], set()
    for url in sources:
        for item in fetch_rss(url, GEO_KW, max_items=6):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key); items.append(item)
    return items[:15]

AI_KW = ["ai","artificial intelligence","llm","gpt","openai","anthropic","gemini",
         "claude","machine learning","deep learning","neural","chatbot","language model",
         "nvidia","automation","robot","agi","generative","deepmind","meta ai","copilot"]

def fetch_ai():
    sources = [
        "https://www.theguardian.com/technology/artificialintelligenceai/rss",
        "https://www.theguardian.com/technology/rss",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://techcrunch.com/feed/",
    ]
    items, seen = [], set()
    for url in sources:
        for item in fetch_rss(url, AI_KW, max_items=6):
            key = item["title"][:50].lower()
            if key not in seen:
                seen.add(key); items.append(item)
    return items[:15]

# ── Senders ───────────────────────────────────────────────────────────────

def send_football(matches):
    msg  = "⚽ <b>FOOTBALL — SCORES &amp; NEWS</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    if not matches:
        msg += "No football news right now.\n"
    else:
        for m in matches:
            msg += f"🔸 <b>{m['title']}</b>\n"
            if m['desc'] and m['desc'].lower() != m['title'].lower():
                msg += f"<i>{m['desc'][:200]}</i>\n"
            if m['link']:
                msg += f"🔗 <a href='{m['link']}'>Full story</a>\n"
            msg += "\n"
    msg += "📡 <i>Premier League | Champions League | La Liga</i>"
    send_message(msg)

def send_trending(trends):
    msg  = "🔥 <b>LATEST TRENDS</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    if not trends:
        msg += "No trending topics right now.\n"
    else:
        for i, t in enumerate(trends, 1):
            msg += f"{i}. 🔺 <b>{t['title']}</b>\n"
            for n in t.get("news", []):
                msg += f"  📰 <i>{n}</i>\n"
            msg += "\n"
    msg += "📡 <i>Google Trends: US | UK | Nepal</i>"
    send_message(msg)

def send_geopolitics(news):
    msg  = "🌍 <b>GEO-POLITICS UPDATE</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    if not news:
        msg += "No geopolitical news right now.\n"
    else:
        for item in news:
            msg += f"🔹 <b>{item['title']}</b>\n"
            if item['desc'] and item['desc'].lower() != item['title'].lower():
                msg += f"<i>{item['desc'][:200]}</i>\n"
            if item['link']:
                msg += f"🔗 <a href='{item['link']}'>Read more</a>\n"
            msg += "\n"
    msg += "📡 <i>The Guardian | BBC World</i>"
    send_message(msg)

def send_ai_news(news):
    msg  = "🤖 <b>AI NEWS</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    if not news:
        msg += "No AI news right now.\n"
    else:
        for item in news:
            msg += f"⚡ <b>{item['title']}</b>\n"
            if item['desc'] and item['desc'].lower() != item['title'].lower():
                msg += f"<i>{item['desc'][:200]}</i>\n"
            if item['link']:
                msg += f"🔗 <a href='{item['link']}'>Read more</a>\n"
            msg += "\n"
    msg += "📡 <i>The Guardian | BBC Tech | TechCrunch</i>"
    send_message(msg)

# ── Briefing & scheduler ──────────────────────────────────────────────────

def send_briefing():
    log("=== Sending briefing ===")
    try:
        send_football(fetch_football());   log("Football sent")
    except Exception as e: log(f"Football error: {e}")
    time.sleep(2)
    try:
        send_trending(fetch_trends());     log("Trends sent")
    except Exception as e: log(f"Trends error: {e}")
    time.sleep(2)
    try:
        send_geopolitics(fetch_geo());     log("Geo sent")
    except Exception as e: log(f"Geo error: {e}")
    time.sleep(2)
    try:
        send_ai_news(fetch_ai());          log("AI sent")
    except Exception as e: log(f"AI error: {e}")
    log("=== Briefing complete ===")

def should_send(last_sent):
    now = nepal_now()
    if last_sent is None: return True
    if now.hour == 6 and now.minute < 2 and last_sent.date() < now.date(): return True
    if (now - last_sent).total_seconds() >= 6 * 3600: return True
    return False

def run_agent():
    if not TOKEN or not CHAT_ID:
        log("ERROR: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID"); return
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
