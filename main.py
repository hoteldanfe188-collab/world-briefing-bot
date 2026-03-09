#!/usr/bin/env python3
"""
World Briefing Bot - Football Scores Only
Premier League | Champions League | La Liga
Schedule: Every 6 hours + 6 AM Nepal time
"""

import requests
import time
import os
from datetime import datetime, timezone, timedelta

TOKEN        = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")

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

# ── League IDs ────────────────────────────────────────────────────────────
LEAGUES = [
    {"id": "39",  "name": "Premier League",    "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    {"id": "2",   "name": "Champions League",  "flag": "🇪🇺"},
    {"id": "140", "name": "La Liga",           "flag": "🇪🇸"},
]

def fetch_fixtures(league_id):
    """Fetch today's fixtures/results for a league"""
    today = nepal_now().strftime("%Y-%m-%d")
    url = "https://football-api7.p.rapidapi.com/Football"
    headers = {
        "x-rapidapi-host": "football-api7.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY,
    }
    params = {
        "endpoint": "fixtures",
        "league":   league_id,
        "season":   "2025",
        "date":     today,
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
        log(f"  API OK league={league_id} -> {len(data.get('response', []))} fixtures")
        return data.get("response", [])
    except Exception as e:
        log(f"  API FAIL league={league_id} -> {e}")
        return []

def format_status(fixture):
    """Return score string or match status"""
    status = fixture.get("fixture", {}).get("status", {}).get("short", "")
    goals  = fixture.get("goals", {})
    home   = fixture.get("teams", {}).get("home", {}).get("name", "?")
    away   = fixture.get("teams", {}).get("away", {}).get("name", "?")
    g_home = goals.get("home")
    g_away = goals.get("away")

    if status in ["FT", "AET", "PEN"]:
        # Full time
        return f"✅ {home} <b>{g_home} — {g_away}</b> {away}"
    elif status in ["1H", "2H", "HT", "ET", "BT", "P", "SUSP", "INT", "LIVE"]:
        # Live
        elapsed = fixture.get("fixture", {}).get("status", {}).get("elapsed", "")
        return f"🔴 LIVE {elapsed}' | {home} <b>{g_home} — {g_away}</b> {away}"
    elif status in ["NS", "TBD"]:
        # Not started
        kickoff = fixture.get("fixture", {}).get("date", "")
        if kickoff:
            try:
                dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
                dt_nepal = dt.astimezone(NEPAL_TZ)
                kickoff  = dt_nepal.strftime("%I:%M %p NST")
            except:
                pass
        return f"🕐 {kickoff} | {home} vs {away}"
    else:
        return f"• {home} vs {away} [{status}]"

def send_football_scores():
    msg  = "⚽ <b>FOOTBALL SCORES</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    any_match = False
    for league in LEAGUES:
        fixtures = fetch_fixtures(league["id"])
        if not fixtures:
            continue
        any_match = True
        msg += f"{league['flag']} <b>{league['name']}</b>\n"
        for fix in fixtures:
            msg += f"  {format_status(fix)}\n"
        msg += "\n"

    if not any_match:
        msg += "No matches scheduled today.\n\n"
        msg += "<i>Check back on match days!</i>\n"

    msg += "📡 <i>Premier League | Champions League | La Liga</i>"
    send_message(msg)

# ── Scheduler ─────────────────────────────────────────────────────────────

def should_send(last_sent):
    now = nepal_now()
    if last_sent is None: return True
    if now.hour == 6 and now.minute < 2 and last_sent.date() < now.date(): return True
    if (now - last_sent).total_seconds() >= 6 * 3600: return True
    return False

def run_agent():
    if not TOKEN or not CHAT_ID or not RAPIDAPI_KEY:
        log("ERROR: Missing env vars (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, RAPIDAPI_KEY)")
        return
    log("Football Scores Bot started!")
    send_football_scores()
    last_sent = nepal_now()
    while True:
        time.sleep(60)
        if should_send(last_sent):
            send_football_scores()
            last_sent = nepal_now()

if __name__ == "__main__":
    run_agent()
