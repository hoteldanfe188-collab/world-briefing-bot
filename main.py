#!/usr/bin/env python3
"""
Football Bot - 2 messages
Message 1: Recent Results
Message 2: Live + Upcoming
Source: football-data.org
"""

import requests
import time
import os
from datetime import datetime, timezone, timedelta

TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID", "")
FD_KEY   = os.environ.get("FD_KEY", "")

NEPAL_TZ = timezone(timedelta(hours=5, minutes=45))

def nepal_now(): return datetime.now(NEPAL_TZ)
def now_str():   return nepal_now().strftime("%d %b %Y, %I:%M %p NST")
def log(msg):    print(f"[{nepal_now().strftime('%H:%M:%S')}] {msg}", flush=True)

# football-data.org competition codes
COMPETITIONS = [
    {"code": "PL",  "name": "Premier League",   "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    {"code": "CL",  "name": "Champions League", "flag": "🇪🇺"},
    {"code": "PD",  "name": "La Liga",          "flag": "🇪🇸"},
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

def fetch_matches(code, date_from, date_to):
    headers = {"X-Auth-Token": FD_KEY}
    params  = {"dateFrom": date_from, "dateTo": date_to, "status": "FINISHED,IN_PLAY,PAUSED,TIMED,SCHEDULED"}
    try:
        r = requests.get(
            f"https://api.football-data.org/v4/competitions/{code}/matches",
            headers=headers, params=params, timeout=12
        )
        r.raise_for_status()
        data    = r.json()
        matches = data.get("matches", [])
        log(f"  OK {code} {date_from}→{date_to} -> {len(matches)} matches")
        return matches
    except Exception as e:
        log(f"  FAIL {code} -> {e}")
        return []

def team_name(name):
    short = {
        "Manchester United FC": "Man Utd",
        "Manchester City FC":   "Man City",
        "Tottenham Hotspur FC": "Spurs",
        "Newcastle United FC":  "Newcastle",
        "Nottingham Forest FC": "Nott'm Forest",
        "Athletic Club":        "Ath. Bilbao",
        "Real Sociedad de Fútbol": "R. Sociedad",
        "Club Atlético de Madrid": "Atlético",
        "FC Internazionale Milano": "Inter",
        "AC Milan":             "Milan",
        "Liverpool FC":         "Liverpool",
        "Arsenal FC":           "Arsenal",
        "Chelsea FC":           "Chelsea",
        "FC Barcelona":         "Barcelona",
        "Real Madrid CF":       "Real Madrid",
        "Galatasaray AŞ":       "Galatasaray",
    }
    return short.get(name, name.replace(" FC", "").replace(" CF", "")[:20])

def nepal_time(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.astimezone(NEPAL_TZ).strftime("%I:%M %p")
    except:
        return ""

def classify(match):
    status = match.get("status", "")
    if status == "FINISHED":
        return "finished"
    elif status in ["IN_PLAY", "PAUSED", "HALFTIME"]:
        return "live"
    else:
        return "upcoming"

def fmt_finished(match):
    home  = team_name(match["homeTeam"]["name"])
    away  = team_name(match["awayTeam"]["name"])
    score = match.get("score", {})
    ft    = score.get("fullTime", {})
    gh    = ft.get("home", "?")
    ga    = ft.get("away", "?")
    if gh != "?" and ga != "?":
        if gh > ga:
            return f"  ✅ <b>{home} {gh}</b> — {ga} {away}"
        elif ga > gh:
            return f"  ✅ {home} {gh} — <b>{ga} {away}</b>"
        else:
            return f"  🤝 {home} {gh} — {ga} {away}"
    return f"  ✅ {home} vs {away}"

def fmt_live(match):
    home  = team_name(match["homeTeam"]["name"])
    away  = team_name(match["awayTeam"]["name"])
    score = match.get("score", {})
    curr  = score.get("fullTime", score.get("halfTime", {}))
    gh    = curr.get("home", "?")
    ga    = curr.get("away", "?")
    minute = match.get("minute", "")
    return f"  🔴 {minute}' | <b>{home} {gh} — {ga} {away}</b>"

def fmt_upcoming(match):
    home = team_name(match["homeTeam"]["name"])
    away = team_name(match["awayTeam"]["name"])
    kt   = nepal_time(match.get("utcDate", ""))
    return f"  🕐 {kt} NST | {home} vs {away}"

def send_recent_results():
    today     = nepal_now()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    tod_str   = today.strftime("%Y-%m-%d")

    msg  = "📋 <b>RECENT RESULTS</b>\n"
    msg += f"🕐 <i>{now_str()}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    any_result = False
    for comp in COMPETITIONS:
        matches = fetch_matches(comp["code"], yesterday, tod_str)
        results = [m for m in matches if classify(m) == "finished"]
        if results:
            any_result = True
            msg += f"{comp['flag']} <b>{comp['name']}</b>\n"
            for m in results:
                msg += fmt_finished(m) + "\n"
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

    for comp in COMPETITIONS:
        matches  = fetch_matches(comp["code"], today, tomorrow)
        live     = [m for m in matches if classify(m) == "live"]
        upcoming = [m for m in matches if classify(m) == "upcoming"]

        if live:
            live_block += f"{comp['flag']} <b>{comp['name']}</b>\n"
            for m in live:
                live_block += fmt_live(m) + "\n"
            live_block += "\n"

        if upcoming:
            upcoming_block += f"{comp['flag']} <b>{comp['name']}</b>\n"
            for m in upcoming[:6]:
                upcoming_block += fmt_upcoming(m) + "\n"
            upcoming_block += "\n"

    msg += "🔴 <b>LIVE NOW</b>\n"
    msg += (live_block if live_block else "No matches live right now.\n") + "\n"

    msg += "📅 <b>UPCOMING</b>\n"
    msg += (upcoming_block if upcoming_block else "No matches today or tomorrow.\n")

    msg += "\n📡 <i>Premier League | Champions League | La Liga</i>"
    send_message(msg)

def send_briefing():
    log("=== Football briefing ===")
    try:
        send_recent_results(); log("Results sent")
    except Exception as e:
        log(f"Results error: {e}")
    time.sleep(2)
    try:
        send_live_and_upcoming(); log("Live/upcoming sent")
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
    if not TOKEN or not CHAT_ID or not FD_KEY:
        log("ERROR: Missing env vars (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, FD_KEY)")
        return
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
