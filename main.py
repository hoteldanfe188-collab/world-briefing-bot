#!/usr/bin/env python3
"""
Football Bot - 2 messages
Message 1: Recent Results
Message 2: Live + Upcoming
Source: api-football.com (api-sports)
"""

import requests
import time
import os
from datetime import datetime, timezone, timedelta

TOKEN        = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "")
APISPORTS_KEY = os.environ.get("APISPORTS_KEY", "")

NEPAL_TZ = timezone(timedelta(hours=5, minutes=45))

def nepal_now(): return datetime.now(NEPAL_TZ)
def now_str():   return nepal_now().strftime("%d %b %Y, %I:%M %p NST")
def log(msg):    print(f"[{nepal_now().strftime('%H:%M:%S')}] {msg}", flush=True)

LEAGUES = [
    {"id": 39,  "name": "Premier League",   "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "season": 2024},
    {"id": 2,   "name": "Champions League", "flag": "🇪🇺",         "season": 2024},
    {"id": 140, "name": "La Liga",          "flag": "🇪🇸",         "season": 2024},
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

def fetch_fixtures(league_id, season, date):
    headers = {
        "x-apisports-key": APISPORTS_KEY,
    }
    params = {
        "league": league_id,
        "season": season,
        "date":   date,
    }
    try:
        r = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers=headers, params=params, timeout=12
        )
        r.raise_for_status()
        data = r.json()
        fixtures = data.get("response", [])
        log(f"  OK league={league_id} date={date} -> {len(fixtures)} fixtures")
        return fixtures
    except Exception as e:
        log(f"  FAIL league={league_id} date={date} -> {e}")
        return []

def team_name(name):
    short = {
        "Manchester United": "Man Utd",
        "Manchester City":   "Man City",
        "Tottenham Hotspur": "Spurs",
        "Newcastle United":  "Newcastle",
        "Nottingham Forest": "Nott'm Forest",
        "Athletic Club":     "Ath. Bilbao",
        "Real Sociedad":     "R. Sociedad",
        "Atletico Madrid":   "Atlético",
        "Inter Milan":       "Inter",
        "AC Milan":          "Milan",
    }
    return short.get(name, name[:20])

def nepal_time(iso_date):
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.astimezone(NEPAL_TZ).strftime("%I:%M %p")
    except:
        return ""

def classify(fix):
    status = fix["fixture"]["status"]["short"]
    if status in ["FT", "AET", "PEN", "AWD", "WO"]:
        return "finished"
    elif status in ["1H", "2H", "HT", "ET", "BT", "P", "SUSP", "INT", "LIVE"]:
        return "live"
    else:
        return "upcoming"

def fmt_finished(fix):
    home = team_name(fix["teams"]["home"]["name"])
    away = team_name(fix["teams"]["away"]["name"])
    gh   = fix["goals"]["home"]
    ga   = fix["goals"]["away"]
    s    = fix["fixture"]["status"]["short"]
    tag  = " (AET)" if s == "AET" else " (PEN)" if s == "PEN" else ""
    # Bold winner
    if gh > ga:
        return f"  ✅ <b>{home} {gh}</b> — {ga} {away}{tag}"
    elif ga > gh:
        return f"  ✅ {home} {gh} — <b>{ga} {away}</b>{tag}"
    else:
        return f"  🤝 {home} {gh} — {ga} {away}{tag}"

def fmt_live(fix):
    home    = team_name(fix["teams"]["home"]["name"])
    away    = team_name(fix["teams"]["away"]["name"])
    gh      = fix["goals"]["home"]
    ga      = fix["goals"]["away"]
    elapsed = fix["fixture"]["status"].get("elapsed", "")
    return f"  🔴 {elapsed}' | <b>{home} {gh} — {ga} {away}</b>"

def fmt_upcoming(fix):
    home = team_name(fix["teams"]["home"]["name"])
    away = team_name(fix["teams"]["away"]["name"])
    kt   = nepal_time(fix["fixture"].get("date", ""))
    return f"  🕐 {kt} NST | {home} vs {away}"

def send_recent_results():
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
            for fix in fetch_fixtures(league["id"], league["season"], date):
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

    msg += "\n📡 <i>Premier League | Champions League | La Liga</i>"
    send_message(msg)

def send_live_and_upcoming():
    today    = nepal_now().strftime("%Y-%m-%d")
    tomorrow = (nepal_now() + timedelta(days=1)).strftime("%Y-%m-%d")

    msg  = "🔴 <b>LIVE &amp; UPCOMING</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    live_block     = ""
    upcoming_block = ""

    for league in LEAGUES:
        live     = []
        upcoming = []
        for date in [today, tomorrow]:
            for fix in fetch_fixtures(league["id"], league["season"], date):
                c = classify(fix)
                if c == "live":     live.append(fix)
                elif c == "upcoming": upcoming.append(fix)

        if live:
            live_block += f"{league['flag']} <b>{league['name']}</b>\n"
            for fix in live:
                live_block += fmt_live(fix) + "\n"
            live_block += "\n"

        if upcoming:
            upcoming_block += f"{league['flag']} <b>{league['name']}</b>\n"
            for fix in upcoming[:5]:
                upcoming_block += fmt_upcoming(fix) + "\n"
            upcoming_block += "\n"

    if live_block:
        msg += "🔴 <b>LIVE NOW</b>\n\n" + live_block
    else:
        msg += "🔴 <b>LIVE NOW</b>\nNo matches live right now.\n\n"

    if upcoming_block:
        msg += "📅 <b>UPCOMING</b>\n\n" + upcoming_block
    else:
        msg += "📅 <b>UPCOMING</b>\nNo matches today or tomorrow.\n"

    msg += "\n📡 <i>Premier League | Champions League | La Liga</i>"
    send_message(msg)

def send_briefing():
    log("=== Football briefing ===")
    try:
        send_recent_results()
        log("Results sent")
    except Exception as e:
        log(f"Results error: {e}")
    time.sleep(2)
    try:
        send_live_and_upcoming()
        log("Live/upcoming sent")
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
    if not TOKEN or not CHAT_ID or not APISPORTS_KEY:
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
