"""
Football Championship - Telegram Bot
Uses only Python stdlib (http.client, json, urllib)
Run: python3 bot.py

Set env vars:
  BOT_TOKEN=your_bot_token_here
  API_URL=http://localhost:3001/api   (your backend)
"""

import os, json, time, urllib.request, urllib.parse

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
API_URL   = os.environ.get("API_URL",   "http://localhost:3001/api")
BASE      = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── per-user conversation state ──────────────────────────────────────────────
user_state = {}   # {user_id: {"step": ..., "data": {...}}}

# ── Telegram helpers ──────────────────────────────────────────────────────────
def tg(method, payload):
    url  = f"{BASE}/{method}"
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[TG ERROR] {method}: {e}")
        return {}

def send(chat_id, text, markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if markup:
        payload["reply_markup"] = markup
    return tg("sendMessage", payload)

def kb(rows):
    """Build an InlineKeyboardMarkup from list of lists of (text, callback_data)."""
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}

# ── Backend helpers ───────────────────────────────────────────────────────────
def api_get(path):
    try:
        with urllib.request.urlopen(API_URL + path, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[API ERROR] GET {path}: {e}")
        return None

def api_post(path, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(API_URL + path, data=data,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[API ERROR] POST {path}: {e}")
        return None

# ── Command handlers ───────────────────────────────────────────────────────────
def cmd_start(msg):
    cid = msg["chat"]["id"]
    name = msg["from"].get("first_name", "there")
    send(cid,
        f"👋 Hello <b>{name}</b>! Welcome to the <b>Football Championship Bot</b>.\n\n"
        "Here's what I can do:\n"
        "📊 /standings — View current league table\n"
        "⚽ /results   — Latest match results\n"
        "📅 /upcoming  — Upcoming fixtures\n"
        "📢 /report    — Report incorrect match info\n"
        "❓ /help      — Show this message")

def cmd_standings(msg):
    cid = msg["chat"]["id"]
    data = api_get("/standings")
    if not data:
        send(cid, "⚠️ Could not fetch standings. Try again later.")
        return
    lines = ["<b>📊 League Table</b>\n"]
    medals = {1:"🥇",2:"🥈",3:"🥉"}
    for s in data:
        p   = s["position"]
        ico = medals.get(p, f"{p}.")
        lines.append(
            f"{ico} <b>{s['name']}</b>\n"
            f"   {s['points']}pts · {s['played']}P {s['won']}W {s['drawn']}D {s['lost']}L · GD {s['goal_difference']:+}"
        )
    send(cid, "\n".join(lines))

def cmd_results(msg):
    cid = msg["chat"]["id"]
    data = api_get("/matches?status=finished&limit=8")
    matches = (data or {}).get("matches", [])
    if not matches:
        send(cid, "No finished matches found yet.")
        return
    lines = ["<b>⚽ Recent Results</b>\n"]
    for m in matches:
        lines.append(
            f"📋 <b>{m['home_team_name']}</b> <code>{m['home_score']} – {m['away_score']}</code> <b>{m['away_team_name']}</b>\n"
            f"   MW{m.get('matchweek',1)} · {m['match_date']} · {m.get('venue','')}"
        )
    send(cid, "\n".join(lines))

def cmd_upcoming(msg):
    cid = msg["chat"]["id"]
    data = api_get("/matches?status=scheduled&limit=8")
    matches = (data or {}).get("matches", [])
    if not matches:
        send(cid, "📅 No upcoming fixtures scheduled yet.")
        return
    lines = ["<b>📅 Upcoming Fixtures</b>\n"]
    for m in matches:
        lines.append(
            f"🔜 <b>{m['home_team_name']}</b> vs <b>{m['away_team_name']}</b>\n"
            f"   MW{m.get('matchweek',1)} · {m['match_date']} · {m.get('venue','TBA')}"
        )
    send(cid, "\n".join(lines))

def cmd_report(msg):
    cid = msg["chat"]["id"]
    uid = msg["from"]["id"]
    user_state[uid] = {"step": "awaiting_name", "data": {}}
    send(cid,
        "📢 <b>Submit a Report</b>\n\n"
        "What's your name? (or type /skip to stay anonymous)")

def cmd_help(msg):
    cmd_start(msg)

# ── Report flow ───────────────────────────────────────────────────────────────
def handle_report_flow(msg):
    cid = msg["chat"]["id"]
    uid = msg["from"]["id"]
    text = msg.get("text", "").strip()
    state = user_state.get(uid, {})
    step  = state.get("step")
    data  = state.get("data", {})

    if step == "awaiting_name":
        data["reporter_name"] = "Anonymous" if text == "/skip" else text
        user_state[uid] = {"step": "awaiting_match_id", "data": data}

        # Show last 5 finished matches as quick picks
        mdata = api_get("/matches?status=finished&limit=5") or {}
        matches = mdata.get("matches", [])
        if matches:
            buttons = [[( f"{m['home_team_name']} {m['home_score']}-{m['away_score']} {m['away_team_name']}",
                          f"match_{m['id']}" )] for m in matches]
            buttons.append([("Skip (no match)", "match_none")])
            send(cid,
                 "Which match is this report about?\n(Or type the match ID manually, or /skip)",
                 markup=kb(buttons))
        else:
            send(cid, "Which match ID is this about? (type /skip if unsure)")

    elif step == "awaiting_match_id":
        if text == "/skip":
            data["match_id"] = None
        else:
            try:
                data["match_id"] = int(text)
            except ValueError:
                data["match_id"] = None
        user_state[uid] = {"step": "awaiting_message", "data": data}
        send(cid, "📝 Please describe the issue:")

    elif step == "awaiting_message":
        data["message"] = text
        # Submit report
        result = api_post("/reports", {
            "match_id":      data.get("match_id"),
            "reporter_name": data.get("reporter_name", "Anonymous"),
            "telegram_user_id": str(uid),
            "message":       data["message"],
        })
        del user_state[uid]
        if result and result.get("id"):
            send(cid,
                 f"✅ <b>Report submitted!</b> (ID #{result['id']})\n\n"
                 "Our admin team will review it shortly. Thank you!")
        else:
            send(cid, "⚠️ Failed to submit report. Please try again later.")

# ── Callback query handler (inline button taps) ───────────────────────────────
def handle_callback(cq):
    uid  = cq["from"]["id"]
    cid  = cq["message"]["chat"]["id"]
    data = cq.get("data", "")
    tg("answerCallbackQuery", {"callback_query_id": cq["id"]})

    state = user_state.get(uid)
    if not state:
        return

    if state["step"] == "awaiting_match_id":
        if data == "match_none":
            state["data"]["match_id"] = None
        elif data.startswith("match_"):
            try:
                state["data"]["match_id"] = int(data.split("_")[1])
            except Exception:
                state["data"]["match_id"] = None
        state["step"] = "awaiting_message"
        user_state[uid] = state
        send(cid, "📝 Now describe the issue in detail:")

# ── Update dispatcher ──────────────────────────────────────────────────────────
def dispatch(update):
    if "callback_query" in update:
        handle_callback(update["callback_query"])
        return

    msg = update.get("message", {})
    if not msg:
        return

    text = msg.get("text", "")
    uid  = msg["from"]["id"]

    # Route commands
    if text.startswith("/start"):    cmd_start(msg)
    elif text.startswith("/standings"): cmd_standings(msg)
    elif text.startswith("/results"):   cmd_results(msg)
    elif text.startswith("/upcoming"):  cmd_upcoming(msg)
    elif text.startswith("/report"):    cmd_report(msg)
    elif text.startswith("/help"):      cmd_help(msg)
    elif uid in user_state:
        handle_report_flow(msg)

# ── Long-polling loop ──────────────────────────────────────────────────────────
def poll():
    offset = 0
    print(f"🤖 Football Bot polling… (token: {BOT_TOKEN[:12]}…)")
    while True:
        try:
            result = tg("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message","callback_query"]})
            for update in (result.get("result") or []):
                offset = update["update_id"] + 1
                try:
                    dispatch(update)
                except Exception as e:
                    print(f"[DISPATCH ERROR] {e}")
        except KeyboardInterrupt:
            print("\n👋 Bot stopped.")
            break
        except Exception as e:
            print(f"[POLL ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️  Set BOT_TOKEN env var:  export BOT_TOKEN=your_token_here")
        print("   Get a token from @BotFather on Telegram\n")
    poll()
