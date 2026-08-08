#!/usr/bin/env python3
"""
XAUUSD Hedge Risk Signals Bot — versione GitHub Actions
==========================================================
A differenza della versione "PC sempre acceso" (xauusd_signals_bot.py),
questo script esegue UN SOLO CICLO e termina: pensato per essere lanciato
periodicamente da un workflow GitHub Actions schedulato (cron), non per
girare in un loop infinito.

Lo stato (candele, posizioni, P&L giornaliero) viene letto/scritto su un
file JSON dentro il repository stesso (state/xauusd_state.json), che il
workflow si occupa di ricommittare ad ogni esecuzione.

Le credenziali Telegram vengono lette da variabili d'ambiente, impostate
nel workflow a partire dai GitHub Secrets — non vanno mai scritte nel codice.
"""

import json
import math
import os
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# ---------------------------------------------------------------------------
# CONFIGURAZIONE (modificabile qui, oppure via variabili d'ambiente nel workflow)
# ---------------------------------------------------------------------------
CFG = {
    "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
    "lot_size": float(os.environ.get("LOT_SIZE", "1.04")),
    "daily_stop": float(os.environ.get("DAILY_STOP", "2700")),
    "daily_target": float(os.environ.get("DAILY_TARGET", "3000")),
    "bucket_seconds": int(os.environ.get("BUCKET_SECONDS", "1800")),  # 30 min, allineato alla cadenza cron consigliata
    "timezone": os.environ.get("PLATFORM_TIMEZONE", "Europe/Rome"),
    "platform_close_hour": int(os.environ.get("PLATFORM_CLOSE_HOUR", "20")),
    "platform_close_minute": int(os.environ.get("PLATFORM_CLOSE_MINUTE", "58")),
}

OZ_PER_LOT = 100
GOLD_API_URL = "https://api.gold-api.com/price/XAU"
STATE_FILE = Path(__file__).resolve().parent / "state" / "xauusd_state.json"

# ---------------------------------------------------------------------------
# INDICATORI
# ---------------------------------------------------------------------------
def ema_series(values, period):
    k = 2 / (period + 1)
    out = []
    for i, v in enumerate(values):
        out.append(v if i == 0 else v * k + out[-1] * (1 - k))
    return out


def rsi_series(closes, period=14):
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    avg_g, avg_l = gains / period, losses / period
    out[period] = 100 - 100 / (1 + (100 if avg_l == 0 else avg_g / avg_l))
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        g, l = max(d, 0), max(-d, 0)
        avg_g = (avg_g * (period - 1) + g) / period
        avg_l = (avg_l * (period - 1) + l) / period
        out[i] = 100 - 100 / (1 + (100 if avg_l == 0 else avg_g / avg_l))
    return out


def macd_hist(closes):
    e12, e26 = ema_series(closes, 12), ema_series(closes, 26)
    line = [a - b for a, b in zip(e12, e26)]
    signal = ema_series(line, 9)
    return [a - b for a, b in zip(line, signal)]


# ---------------------------------------------------------------------------
# STATO (persistito nel file dentro il repo)
# ---------------------------------------------------------------------------
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "day": date.today().isoformat(),
        "day_status": "active",
        "session_closed_today": False,
        "closes": [],
        "bucket_start": None,
        "bucket_o": None, "bucket_h": None, "bucket_l": None, "bucket_c": None,
        "trades": [],
        "last_signal_key": None,
        "telegram_offset": 0,
    }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# TELEGRAM
# ---------------------------------------------------------------------------
def tg_send(text):
    if not CFG["telegram_bot_token"] or not CFG["telegram_chat_id"]:
        print(f"[telegram non configurato] {text}")
        return
    try:
        url = f"https://api.telegram.org/bot{CFG['telegram_bot_token']}/sendMessage"
        r = requests.post(url, json={"chat_id": CFG["telegram_chat_id"], "text": text}, timeout=10)
        if not r.ok:
            print(f"[errore invio telegram] {r.text}")
    except Exception as e:
        print(f"[errore invio telegram] {e}")


def tg_get_updates(offset):
    if not CFG["telegram_bot_token"]:
        return [], offset
    try:
        url = f"https://api.telegram.org/bot{CFG['telegram_bot_token']}/getUpdates"
        r = requests.get(url, params={"offset": offset, "timeout": 0}, timeout=8)
        data = r.json()
        updates = data.get("result", [])
        new_offset = offset
        for u in updates:
            new_offset = max(new_offset, u["update_id"] + 1)
        return updates, new_offset
    except Exception as e:
        print(f"[errore lettura telegram] {e}")
        return [], offset


# ---------------------------------------------------------------------------
# P&L GIORNALIERO
# ---------------------------------------------------------------------------
def compute_daily_pnl(state, price):
    today = date.today().isoformat()
    closed = sum(t["pnl"] for t in state["trades"] if not t["open"] and t.get("day") == today)
    open_trade = next((t for t in state["trades"] if t["open"]), None)
    floating = 0.0
    if open_trade and price:
        diff = (price - open_trade["entry"]) if open_trade["dir"] == "BUY" else (open_trade["entry"] - price)
        floating = diff * open_trade["lots"] * OZ_PER_LOT
    return closed + floating, open_trade, floating


def check_daily_reset(state):
    today = date.today().isoformat()
    if state["day"] != today:
        state["day"] = today
        state["day_status"] = "active"
        state["session_closed_today"] = False
        print(f"[nuovo giorno] governatore di rischio riattivato ({today})")


def trading_allowed(state):
    return state["day_status"] == "active" and not state["session_closed_today"]


def enforce_platform_close(state, price):
    """La piattaforma chiude automaticamente le posizioni entro le 20:58 ora
    italiana. Se c'è ancora una posizione aperta a quell'ora, la chiudiamo
    anche noi nello stato interno (allo stesso prezzo corrente) così il P&L
    giornaliero resta coerente con quello che succede davvero sul conto, e
    blocchiamo nuovi segnali/posizioni per il resto della sessione odierna.
    """
    if state["session_closed_today"]:
        return
    now_local = datetime.now(ZoneInfo(CFG["timezone"]))
    close_at = now_local.replace(
        hour=CFG["platform_close_hour"], minute=CFG["platform_close_minute"], second=0, microsecond=0
    )
    if now_local < close_at:
        return

    open_trade = next((t for t in state["trades"] if t["open"]), None)
    if open_trade:
        diff = (price - open_trade["entry"]) if open_trade["dir"] == "BUY" else (open_trade["entry"] - price)
        pnl = diff * open_trade["lots"] * OZ_PER_LOT
        open_trade["open"] = False
        open_trade["exit"] = price
        open_trade["pnl"] = pnl
        tg_send(
            f"🔒 Chiusura automatica piattaforma (20:58)\n"
            f"Posizione {open_trade['dir']} chiusa @ {price:.2f} — P&L: {pnl:+.2f}$"
        )
    state["session_closed_today"] = True
    print("[sessione chiusa] oltre l'orario di chiusura piattaforma, segnali sospesi fino a domani.")


def handle_command(state, text, price):
    parts = text.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()

    if cmd == "/apri":
        if not trading_allowed(state):
            reason = "sessione chiusa dalla piattaforma (dopo le 20:58)" if state["session_closed_today"] else "governatore di rischio non attivo oggi"
            tg_send(f"⛔ Nuove posizioni bloccate: {reason}.")
            return
        if len(parts) < 2 or parts[1].upper() not in ("BUY", "SELL"):
            tg_send("Uso: /apri BUY|SELL [prezzo] [lotti]")
            return
        direction = parts[1].upper()
        entry = float(parts[2]) if len(parts) > 2 else price
        lots = float(parts[3]) if len(parts) > 3 else CFG["lot_size"]
        if any(t["open"] for t in state["trades"]):
            tg_send("C'è già una posizione aperta. Chiudila prima con /chiudi.")
            return
        state["trades"].append({
            "dir": direction, "entry": entry, "exit": None, "lots": lots,
            "pnl": 0.0, "open": True, "time": datetime.now().isoformat(), "day": date.today().isoformat(),
        })
        tg_send(f"✅ Posizione aperta: {direction} @ {entry:.2f} ({lots} lotti)")

    elif cmd == "/chiudi":
        open_trade = next((t for t in state["trades"] if t["open"]), None)
        if not open_trade:
            tg_send("Nessuna posizione aperta da chiudere.")
            return
        exit_price = float(parts[1]) if len(parts) > 1 else price
        diff = (exit_price - open_trade["entry"]) if open_trade["dir"] == "BUY" else (open_trade["entry"] - exit_price)
        pnl = diff * open_trade["lots"] * OZ_PER_LOT
        open_trade["open"] = False
        open_trade["exit"] = exit_price
        open_trade["pnl"] = pnl
        tg_send(f"✅ Posizione chiusa @ {exit_price:.2f} — P&L: {pnl:+.2f}$")

    elif cmd == "/stato":
        pnl, open_trade, floating = compute_daily_pnl(state, price)
        msg = (
            f"📊 Stato giornaliero\n"
            f"Prezzo attuale: {price:.2f}\n"
            f"P&L oggi: {pnl:+.2f}$ (stop -{CFG['daily_stop']:.0f}$ / target +{CFG['daily_target']:.0f}$)\n"
            f"Stato: {state['day_status']}"
            + (" (sessione chiusa dalla piattaforma)" if state["session_closed_today"] else "")
            + "\n"
        )
        msg += (f"Posizione aperta: {open_trade['dir']} @ {open_trade['entry']:.2f} (flottante {floating:+.2f}$)"
                if open_trade else "Nessuna posizione aperta.")
        tg_send(msg)

    elif cmd == "/reset":
        state["day_status"] = "active"
        tg_send("🔓 Blocco giornaliero rimosso manualmente. Usa con cautela.")


# ---------------------------------------------------------------------------
# UN SOLO CICLO — chiamato dal workflow ad ogni esecuzione schedulata
# ---------------------------------------------------------------------------
def run_once():
    state = load_state()
    check_daily_reset(state)

    resp = requests.get(GOLD_API_URL, timeout=10)
    resp.raise_for_status()
    price = float(resp.json()["price"])
    print(f"Prezzo XAU/USD: {price:.2f}")

    enforce_platform_close(state, price)

    bucket_sec = CFG["bucket_seconds"]
    now_bucket = math.floor(time.time() / bucket_sec) * bucket_sec
    if state["bucket_start"] != now_bucket:
        if state["bucket_start"] is not None:
            state["closes"] = (state["closes"] + [state["bucket_c"]])[-150:]
        state["bucket_start"] = now_bucket
        state["bucket_o"] = state["bucket_h"] = state["bucket_l"] = state["bucket_c"] = price
    else:
        state["bucket_h"] = max(state["bucket_h"], price)
        state["bucket_l"] = min(state["bucket_l"], price)
        state["bucket_c"] = price

    closes = state["closes"] + [state["bucket_c"]]

    if len(closes) > 30:
        e9, e21 = ema_series(closes, 9), ema_series(closes, 21)
        r = rsi_series(closes, 14)
        hist = macd_hist(closes)
        i = len(closes) - 1
        cross_up = e9[i - 1] <= e21[i - 1] and e9[i] > e21[i]
        cross_down = e9[i - 1] >= e21[i - 1] and e9[i] < e21[i]

        sig_type, reason = None, ""
        if cross_up and r[i] and r[i] > 50 and hist[i] > 0:
            sig_type, reason = "BUY", "EMA9 incrocia sopra EMA21, RSI>50, MACD istogramma positivo"
        elif cross_down and r[i] and r[i] < 50 and hist[i] < 0:
            sig_type, reason = "SELL", "EMA9 incrocia sotto EMA21, RSI<50, MACD istogramma negativo"

        if sig_type:
            sig_key = f"{sig_type}-{len(closes)}"
            if sig_key != state["last_signal_key"]:
                state["last_signal_key"] = sig_key
                pnl, _, _ = compute_daily_pnl(state, price)
                if trading_allowed(state):
                    tg_send(
                        f"📡 SEGNALE XAUUSD — {sig_type}\n"
                        f"Prezzo: {price:.2f}\n"
                        f"Motivo: {reason}\n"
                        f"Lotti suggeriti: {CFG['lot_size']}\n"
                        f"P&L oggi: {pnl:+.2f}$"
                    )
                else:
                    print(f"[segnale sospeso: sessione non attiva] {sig_type} @ {price:.2f}")

    pnl, _, _ = compute_daily_pnl(state, price)
    if state["day_status"] == "active":
        if pnl <= -abs(CFG["daily_stop"]):
            state["day_status"] = "stopped"
            tg_send(f"🛑 STOP LOSS GIORNALIERO RAGGIUNTO\nP&L oggi: {pnl:+.2f}$\nSegnali sospesi fino a domani.")
        elif pnl >= abs(CFG["daily_target"]):
            state["day_status"] = "target"
            tg_send(f"🎯 TAKE PROFIT GIORNALIERO RAGGIUNTO\nP&L oggi: {pnl:+.2f}$\nSegnali sospesi fino a domani.")

    updates, new_offset = tg_get_updates(state["telegram_offset"])
    state["telegram_offset"] = new_offset
    for u in updates:
        text = u.get("message", {}).get("text", "")
        if text.startswith("/"):
            handle_command(state, text, price)

    save_state(state)
    print(f"Ciclo completato. P&L oggi: {pnl:+.2f}$ — stato: {state['day_status']}")


if __name__ == "__main__":
    run_once()
