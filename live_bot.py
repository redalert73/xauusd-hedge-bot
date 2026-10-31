# ==========================================
# LIVE BOT - HEDGE XAU/USD (un ciclo per esecuzione)
# ==========================================
# Pensato per GitHub Actions ogni 5 minuti. Ogni esecuzione:
#   1. scarica le candele M5 da Twelve Data (scarta quella ancora in corso)
#   2. aggiorna TUTTI i segnali ancora aperti (SL / TP / slippage / chiusura 21:45)
#   3. cerca un nuovo segnale (solo 06:00-20:00 ora italiana)
#   4. legge i comandi Telegram (/stato /stop /riprendi /fatto)
#
# Con SINGLE_POSITION (default) c'e' una sola posizione alla volta: nessun nuovo segnale
# finche' quello aperto non si chiude, e dopo uno SL niente altri segnali per quel giorno.
# Con SINGLE_POSITION = False i segnali sono indipendenti (piu' posizioni insieme).
#
# Log volutamente scarni: nei repo pubblici i log di Actions sono leggibili.

import json
import os
from pathlib import Path

import pandas as pd
import requests

import config
import hedge_core as core
import notifier
from strategies import strategy_hedge

STATE_FILE = Path(__file__).resolve().parent / "state" / "xauusd_state.json"
SCHEMA = 3
TD_URL = "https://api.twelvedata.com/time_series"


# ---------- stato ----------
def new_state(day):
    return {
        "schema": SCHEMA,
        "day": day,
        "signals_today": 0,
        "paused": False,
        "done_today": False,       # /fatto: hai gia' toccato lo SL, niente altri segnali oggi
        "positions": [],           # segnali ancora aperti
        "last_signal_candle": None,
        "tg_offset": 0,
        "summary_sent": False,
        "stats": {"SL": 0, "TP": 0, "AMBIGUO": 0, "CHIUSURA": 0, "pnl_usd": 0.0, "slip_alerts": 0},
    }


def load_state(day):
    try:
        st = json.loads(STATE_FILE.read_text())
        if st.get("schema") != SCHEMA:
            raise ValueError("schema vecchio")
    except Exception:
        return new_state(day)
    if st["day"] != day:  # nuovo giorno: azzero i contatori, tengo offset Telegram e posizioni non chiuse
        fresh = new_state(day)
        fresh["tg_offset"] = st.get("tg_offset", 0)
        fresh["positions"] = st.get("positions", [])
        return fresh
    return st


def save_state(st):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, indent=2))


# ---------- dati ----------
def download_candles(now_utc=None):
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("TWELVE_DATA_API_KEY mancante.")
        return None
    try:
        r = requests.get(
            TD_URL,
            params={
                "symbol": config.SYMBOL, "interval": config.TIMEFRAME,
                "outputsize": config.CANDLES_TO_FETCH, "timezone": "UTC",
                "order": "ASC", "apikey": api_key,
            },
            timeout=15,
        )
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"Errore Twelve Data: {type(e).__name__}")
        return None
    if data.get("status") == "error" or "values" not in data:
        print(f"Twelve Data: {data.get('code')} {str(data.get('message'))[:150]}")
        return None

    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])

    # scarto la candela ancora in corso (il suo segnale potrebbe sparire a chiusura)
    now_utc = now_utc if now_utc is not None else pd.Timestamp.now(tz="UTC").tz_localize(None)
    if len(df) and df.index[-1] + pd.Timedelta(minutes=core.CANDLE_MIN) > now_utc:
        df = df.iloc[:-1]
    return df if len(df) else None


# ---------- messaggi ----------
def p2(x):
    return f"{x:,.2f}"


def signal_message(sig, loser, mirror, when_rome):
    level = sig.get("relax", 0)
    note = {
        0: "Filtri: selettivi",
        1: "Filtri: allargati (ritmo segnali sotto target)",
        2: "Filtri: minimi, segnale di QUOTA (serve a mantenere il ritmo, nessun vantaggio statistico)",
    }[level]
    return (
        "SEGNALE HEDGE XAU/USD\n"
        f"Candela chiusa alle {when_rome:%H:%M} (ora IT) | ATR {sig['atr']:.1f} | RSI {sig['rsi']:.0f}\n"
        f"Regime {sig.get('regime', '-')} | ER {sig.get('er', float('nan')):.2f} | "
        f"VWAP sessione {sig.get('vwap', float('nan')):,.2f}\n"
        f"{note}\n\n"
        f"BROKER PERDENTE: {loser['dir']} {config.LOT_SIZE} @ {p2(loser['entry'])} (conto virtuale)\n"
        f"  SL obiettivo {p2(loser['sl'])}  ({core.fmt_usd(-config.SL_USD, True)})\n"
        f"  TP da evitare {p2(loser['tp'])}  ({core.fmt_usd(config.TP_USD, True)})\n"
        f"  Limite slippage {p2(loser['slip'])}  ({core.fmt_usd(-config.SLIPPAGE_MAX_USD, True)}) MAI da raggiungere\n\n"
        f"BROKER SPECULARE (reale): {mirror['dir']} {config.MIRROR_LOT} @ {p2(mirror['entry'])}\n"
        f"  TP {p2(mirror['tp'])}  ({core.fmt_usd(config.SL_USD * config.MIRROR_LOT_RATIO, True)})\n"
        f"  SL {p2(mirror['sl'])}  ({core.fmt_usd(-config.TP_USD * config.MIRROR_LOT_RATIO, True)})\n\n"
        f"Distanze dal tuo prezzo di ingresso: SL {config.SL_POINTS:.2f} pt | TP {config.TP_POINTS:.2f} pt | "
        f"slippage {config.SLIPPAGE_POINTS:.2f} pt\n"
        f"(i livelli sopra partono dalla chiusura della candela: se entri a un prezzo diverso, applica le stesse distanze)\n\n"
        f"Chiusura automatica: {config.FORCE_CLOSE:%H:%M} | Segnale n. {{n}} di oggi"
        + ("\nPosizione unica: non ne apro altre finche' non ti scrivo l'esito." if config.SINGLE_POSITION else "")
        + (f"\nSe lo apri, scrivi /eseguito entro {config.CONFIRM_TIMEOUT_MIN} minuti: solo allora lo seguo." if config.REQUIRE_CONFIRMATION else "")
    )


# ---------- aggiornamento dei segnali aperti ----------
def manage_positions(st, df, now_rome):
    stats = st["stats"]
    r = config.MIRROR_LOT_RATIO
    remaining = []

    for op in st["positions"]:
        start = pd.Timestamp(op["candle_start"])
        label = f"{core.candle_end_rome(start):%H:%M}"
        loser, _ = core.levels(op["entry"], op["loser"])
        resolved = False

        if not op.get("confirmed", True):
            age_min = (now_rome - core.candle_end_rome(start)).total_seconds() / 60
            if age_min > config.CONFIRM_TIMEOUT_MIN or core.at_or_past_force_close(now_rome):
                st["signals_today"] = max(0, st["signals_today"] - 1)
                notifier.send_notification(
                    f"Segnale delle {label} scaduto: non confermato con /eseguito, non lo seguo e non conta."
                )
            else:
                remaining.append(op)
            continue

        for ts, b in df[df.index > start].iterrows():
            outcome, slip, adverse_usd = core.step_outcome(op["loser"], op["entry"], b["high"], b["low"])
            if slip:
                stats["slip_alerts"] += 1
                notifier.send_notification(
                    "ATTENZIONE SLIPPAGE\n"
                    f"Segnale delle {label}: nella candela delle {core.to_rome(ts):%H:%M} il prezzo ha percorso "
                    f"{core.fmt_usd(adverse_usd)} contro il perdente, oltre il limite di "
                    f"{core.fmt_usd(config.SLIPPAGE_MAX_USD)}.\nVerifica subito il fill reale sul broker."
                )
            if outcome in ("SL", "TP", "AMBIGUO"):
                exit_price = loser["sl"] if outcome == "SL" else loser["tp"]
                pnl = -config.SL_USD if outcome == "SL" else config.TP_USD
                stats[outcome] += 1
                stats["pnl_usd"] += pnl
                if outcome == "SL":
                    txt = (f"OBIETTIVO RAGGIUNTO sul segnale delle {label}: SL toccato sul perdente "
                           f"({core.fmt_usd(-config.SL_USD, True)}).\n"
                           f"Lo speculare e' in TP ({core.fmt_usd(config.SL_USD * r, True)}): chiudi entrambe se non gia' fatto.\n")
                    txt += "Per oggi hai finito: nessun altro segnale."
                elif outcome == "TP":
                    txt = (f"ESITO DA EVITARE sul segnale delle {label}: TP toccato sul perdente "
                           f"({core.fmt_usd(config.TP_USD, True)}).\n"
                           f"Lo speculare e' in SL ({core.fmt_usd(-config.TP_USD * r, True)}): chiudi entrambe se non gia' fatto.")
                else:
                    txt = (f"Segnale delle {label}: SL e TP toccati nella stessa candela M5, ordine non ricostruibile.\n"
                           "Controlla sul broker come si sono chiuse le due gambe.")
                notifier.send_notification(f"{txt}\nCandela {core.to_rome(ts):%H:%M} | livello {p2(exit_price)}")
                resolved = True
                break
        if resolved:
            continue

        # nessun SL/TP: chiusura forzata a fine sessione (o a inizio giorno dopo, se rimasto aperto)
        if core.at_or_past_force_close(now_rome) or core.to_rome(start).date() != now_rome.date():
            last_close = float(df["close"].iloc[-1])
            pnl = core.pnl_usd(op["loser"], op["entry"], last_close)
            stats["CHIUSURA"] += 1
            stats["pnl_usd"] += pnl
            notifier.send_notification(
                f"CHIUSURA AUTOMATICA {config.FORCE_CLOSE:%H:%M}\n"
                f"Segnale delle {label}: perdente chiuso a ~{p2(last_close)}: {core.fmt_usd(pnl, True)}. "
                f"Speculare: {core.fmt_usd(-pnl * r, True)} (prima di spread/commissioni)."
            )
            continue
        remaining.append(op)

    st["positions"] = remaining


# ---------- nuovo segnale ----------
def maybe_new_signal(st, df, now_rome):
    if st["paused"] or st.get("done_today"):
        return
    if config.SINGLE_POSITION and st["positions"]:
        return  # una posizione alla volta: aspetto l'esito di quella aperta
    if config.MAX_SIGNALS_PER_DAY and st["signals_today"] >= config.MAX_SIGNALS_PER_DAY:
        return

    last_start = df.index[-1]
    end_rome = core.candle_end_rome(last_start)
    age_min = (now_rome - end_rome).total_seconds() / 60
    if age_min > config.MAX_SIGNAL_AGE_MIN or age_min < -1:
        return  # dati non freschi (mercato chiuso o ritardo): troppo tardi per entrare
    if not core.in_signal_window(end_rome) or not core.in_signal_window(now_rome):
        return
    if st["last_signal_candle"] == str(last_start):
        return
    gap = None
    if st["last_signal_candle"]:
        gap = (last_start - pd.Timestamp(st["last_signal_candle"])).total_seconds() / 60
    if not core.gap_ok(gap):
        return

    level_max = core.max_relax_level(st["signals_today"], core.minutes_of(end_rome))
    sig = strategy_hedge.check_last(df, relax=level_max)
    if not sig:
        return

    loser, mirror = core.levels(sig["price"], sig["loser"])
    st["signals_today"] += 1
    prev_candle = st["last_signal_candle"]
    st["last_signal_candle"] = str(last_start)
    text = signal_message(sig, loser, mirror, end_rome).replace("{n}", str(st["signals_today"]))
    if notifier.send_notification(text):
        st["positions"].append({
            "candle_start": str(last_start), "loser": sig["loser"], "entry": sig["price"],
            "relax": sig.get("relax", 0),
            "confirmed": not config.REQUIRE_CONFIRMATION,
        })
        print("Segnale inviato.")
    else:
        st["signals_today"] -= 1  # invio fallito: riprovo alla prossima esecuzione
        st["last_signal_candle"] = prev_candle


# ---------- comandi e riepilogo ----------
def handle_commands(st):
    cmds, st["tg_offset"] = notifier.fetch_commands(st["tg_offset"])
    for c in cmds:
        if c in ("/stop", "/ferma", "/pausa"):
            st["paused"] = True
            notifier.send_notification("Nuovi segnali in pausa. I segnali aperti restano monitorati. /riprendi per riattivare.")
        elif c == "/riprendi":
            st["paused"] = False
            st["done_today"] = False
            notifier.send_notification("Segnali riattivati.")
        elif c in ("/eseguito", "/preso", "/ok"):
            pend = [op for op in st["positions"] if not op.get("confirmed", True)]
            if not pend:
                notifier.send_notification("Nessun segnale in attesa di conferma.")
            for op in pend:
                op["confirmed"] = True
                if config.STOP_AFTER_EXECUTION:
                    st["done_today"] = True
                lab = core.candle_end_rome(pd.Timestamp(op["candle_start"])).strftime("%H:%M")
                notifier.send_notification(f"Ricevuto: segnale delle {lab} eseguito. Lo monitoro fino a SL/TP/{config.FORCE_CLOSE:%H:%M}."
                                           + (" Nessun altro segnale oggi." if config.STOP_AFTER_EXECUTION else ""))
        elif c == "/fatto":
            st["done_today"] = True
            notifier.send_notification("Ricevuto: obiettivo SL di oggi segnato come fatto. Nessun altro segnale fino a domani "
                                       "(i segnali aperti restano monitorati). /riprendi per riattivare.")
        elif c == "/stato":
            s = st["stats"]
            notifier.send_notification(
                f"STATO {st['day']}\n"
                f"Segnali oggi: {st['signals_today']} | "
                f"Pausa: {'si' if st['paused'] else 'no'} | Fatto: {'si' if st.get('done_today') else 'no'}\n"
                f"Esiti: SL {s['SL']} | TP {s['TP']} | Chiusura {s['CHIUSURA']} | Ambigui {s['AMBIGUO']}\n"
                f"SL virtuale toccato oggi: {'si' if s['SL'] else 'non ancora'}\n"
                f"P&L perdente (virtuale): {core.fmt_usd(s['pnl_usd'], True)} | "
                f"speculare (reale): {core.fmt_usd(-s['pnl_usd'] * config.MIRROR_LOT_RATIO, True)}\n"
                f"Segnali seguiti: {sum(1 for o in st['positions'] if o.get('confirmed', True))} | "
                f"in attesa di conferma: {sum(1 for o in st['positions'] if not o.get('confirmed', True))}"
            )


def maybe_summary(st, now_rome):
    if st["summary_sent"] or not core.at_or_past_force_close(now_rome) or st["positions"]:
        return
    if st["signals_today"] == 0:
        notifier.send_notification(f"RIEPILOGO {st['day']}\nNessun segnale oggi: obiettivo SL NON raggiunto.")
        st["summary_sent"] = True
        return
    s = st["stats"]
    notifier.send_notification(
        f"RIEPILOGO {st['day']}\n"
        f"Segnali: {st['signals_today']} | SL {s['SL']} | TP {s['TP']} | Chiusura {s['CHIUSURA']} | Ambigui {s['AMBIGUO']}\n"
        f"Obiettivo SL del giorno (virtuale): {'RAGGIUNTO' if s['SL'] else 'NON raggiunto'}\n"
        f"P&L perdente (virtuale): {core.fmt_usd(s['pnl_usd'], True)}\n"
        f"P&L speculare (reale, lotti x{config.MIRROR_LOT_RATIO:g}): "
        f"{core.fmt_usd(-s['pnl_usd'] * config.MIRROR_LOT_RATIO, True)} (prima di spread/commissioni)"
    )
    st["summary_sent"] = True


# ---------- main ----------
def run_production(now_rome=None):
    now_rome = now_rome if now_rome is not None else pd.Timestamp.now(tz=config.TIMEZONE)
    now_utc = now_rome.tz_convert("UTC").tz_localize(None)
    if now_rome.weekday() >= 5:
        return  # sabato/domenica: mercato chiuso

    st = load_state(now_rome.strftime("%Y-%m-%d"))
    handle_commands(st)

    needs_data = bool(st["positions"]) or core.in_signal_window(now_rome)
    if needs_data:
        df = download_candles(now_utc)
        if df is not None:
            manage_positions(st, df, now_rome)
            maybe_new_signal(st, df, now_rome)
        elif st["positions"] and core.at_or_past_force_close(now_rome):
            notifier.send_notification(
                f"CHIUSURA {config.FORCE_CLOSE:%H:%M}: dati non disponibili, chiudi a mano tutte le posizioni aperte."
            )
            st["positions"] = []

    maybe_summary(st, now_rome)
    save_state(st)


if __name__ == "__main__":
    run_production()
