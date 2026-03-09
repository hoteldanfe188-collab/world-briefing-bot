#!/usr/bin/env python3
"""
Football Bot - 2 messages
Message 1: Recent Results
Message 2: Live + Upcoming
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

LEAGUES = [
    {"id": "39",  "name": "Premier League",   "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    {"id": "2",   "name": "Champions League", "flag": "🇪🇺"},
    {"id": "140", "name": "La Liga",          "flag": "🇪🇸"},
]

def send_message(text):
    try:
        if len(text) > 4096:
            text = text[:4090] + "..."
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
        log("Sent!" if r.status_code == 200 else f"TG error: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log(f"TG error: {e}")

def fetch_fixtures(league_id, date):
    url = "https://football-api7.p.rapidapi.com/Football"
    headers = {
        "x-rapidapi-host": "football-api7.p.rapidapi.com",
        "x-rapidapi-key":  RAPIDAPI_KEY,
    }
    params = {"endpoint": "fixtures", "league": league_id, "season": "2025", "date": date}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
        fixtures = data.get("response", [])
        log(f"  API OK league={league_id} date={date} -> {len(fixtures)} fixtures")
        return fixtures
    except Exception as e:
        log(f"  API FAIL league={league_id} -> {e}")
        return []

def team_name(name, max_len=18):
    """Shorten long team names"""
    short = {
        "Manchester United": "Man United",
        "Manchester City":   "Man City",
        "Tottenham Hotspur": "Spurs",
        "Newcastle United":  "Newcastle",
        "Nottingham Forest": "Nott'm Forest",
        "Athletic Club":     "Athletic Bilbao",
        "Real Sociedad":     "R. Sociedad",
        "Atletico Madrid":   "Atlético",
    }
    return short.get(name, name[:max_len])

def nepal_time(iso_date):
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.astimezone(NEPAL_TZ).strftime("%I:%M %p NST")
    except:
        return ""

def classify(fix):
    status = fix.get("fixture", {}).get("status", {}).get("short", "")
    if status in ["FT", "AET", "PEN", "AWD", "WO"]:
        return "finished"
    elif status in ["1H", "2H", "HT", "ET", "BT", "P", "SUSP", "INT", "LIVE"]:
        return "live"
    else:
        return "upcoming"

def fmt_finished(fix):
    home   = team_name(fix["teams"]["home"]["name"])
    away   = team_name(fix["teams"]["away"]["name"])
    gh     = fix["goals"]["home"]
    ga     = fix["goals"]["away"]
    status = fix["fixture"]["status"]["short"]
    suffix = " (AET)" if status == "AET" else " (PEN)" if status == "PEN" else ""
    return f"  ✅ {home} <b>{gh} — {ga}</b> {away}{suffix}"

def fmt_live(fix):
    home    = team_name(fix["teams"]["home"]["name"])
    away    = team_name(fix["teams"]["away"]["name"])
    gh      = fix["goals"]["home"]
    ga      = fix["goals"]["away"]
    elapsed = fix["fixture"]["status"].get("elapsed", "")
    return f"  🔴 {elapsed}' | {home} <b>{gh} — {ga}</b> {away}"

def fmt_upcoming(fix):
    home    = team_name(fix["teams"]["home"]["name"])
    away    = team_name(fix["teams"]["away"]["name"])
    kt      = nepal_time(fix["fixture"].get("date", ""))
    return f"  🕐 {kt} | {home} vs {away}"

def send_recent_results():
    """Message 1: Yesterday + today's finished matches"""
    today     = nepal_now()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    tod_str   = today.strftime("%Y-%m-%d")

    msg  = "📋 <b>RECENT RESULTS</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    any_result = False
    for league in LEAGUES:
        results = []
        for date in [yesterday, tod_str]:
            for fix in fetch_fixtures(league["id"], date):
                if classify(fix) == "finished":
                    results.append(fix)
        if results:
            any_result = True
            msg += f"{league['flag']} <b>{league['name']}</b>\n"
            for fix in results:
                msg += fmt_finished(fix) + "\n"
            msg += "\n"

    if not any_result:
        msg += "No recent results in the last 2 days.\n"

    msg += "📡 <i>Premier League | Champions League | La Liga</i>"
    send_message(msg)

def send_live_and_upcoming():
    """Message 2: Live now + today's upcoming matches"""
    today   = nepal_now().strftime("%Y-%m-%d")
    tomorrow = (nepal_now() + timedelta(days=1)).strftime("%Y-%m-%d")

    msg  = "🔴 <b>LIVE &amp; UPCOMING MATCHES</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    live_section     = ""
    upcoming_section = ""

    for league in LEAGUES:
        live     = []
        upcoming = []
        for date in [today, tomorrow]:
            for fix in fetch_fixtures(league["id"], date):
                c = classify(fix)
                if c == "live":
                    live.append(fix)
                elif c == "upcoming":
                    upcoming.append(fix)

        if live:
            live_section += f"{league['flag']} <b>{league['name']}</b>\n"
            for fix in live:
                live_section += fmt_live(fix) + "\n"
            live_section += "\n"

        if upcoming:
            upcoming_section += f"{league['flag']} <b>{league['name']}</b>\n"
            for fix in upcoming[:5]:
                upcoming_section += fmt_upcoming(fix) + "\n"
            upcoming_section += "\n"

    if live_section:
        msg += "🔴 <b>LIVE NOW:</b>\n\n" + live_section
    else:
        msg += "🔴 <b>LIVE NOW:</b>\nNo matches live right now.\n\n"

    if upcoming_section:
        msg += "📅 <b>UPCOMING:</b>\n\n" + upcoming_section
    else:
        msg += "📅 <b>UPCOMING:</b>\nNo upcoming matches today or tomorrow.\n"

    msg += "📡 <i>Premier League | Champions League | La Liga</i>"
    send_message(msg)

def send_briefing():
    log("=== Sending football briefing ===")
    try:
        send_recent_results()
        log("Recent results sent")
    except Exception as e:
        log(f"Results error: {e}")
    time.sleep(2)
    try:
        send_live_and_upcoming()
        log("Live & upcoming sent")
    except Exception as e:
        log(f"Live error: {e}")
    log("=== Done ===")

def should_send(last_sent):
    now = nepal_now()
    if last_sent is None: return True
    if now.hour == 6 and now.minute < 2 and last_sent.date() < now.date(): return True
    if (now - last_sent).total_seconds() >= 6 * 3600: return True
    return False

def run_agent():
    if not TOKEN or not CHAT_ID or not RAPIDAPI_KEY:
        log("ERROR: Missing env vars"); return
    log("Football Bot started!")
    send_briefing()
    last_sent = nepal_now()
    while True:
        time.sleep(60)
        if should_send(last_sent):
            send_briefing()
            last_sent = nepal_now()

if __name__ == "__main__":
    run_agent()
