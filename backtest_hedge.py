# ==========================================
# BACKTEST HEDGE XAU/USD - DATI REALI TWELVE DATA
# ==========================================
# Misura una cosa sola: quante volte la gamba PERDENTE tocca lo SL (2.200$)
# prima del TP (2.000$), con le stesse regole del bot live.
#
# Uso:
#   python backtest_hedge.py --pages 6            # parametri attuali della strategia
#   python backtest_hedge.py --pages 6 --optimize # ricerca parametri + verifica fuori campione
#   python backtest_hedge.py --csv dati.csv       # dati da file (datetime,open,high,low,close, UTC)
#
# Riferimento da battere: un ingresso senza alcun criterio tocca lo SL per primo
# solo ~47.6% delle volte (il TP e' piu' vicino dello SL). Un risultato
# non chiaramente sopra questa soglia, fuori campione, NON e' un vantaggio.

import argparse
from datetime import time
import itertools
import math
import os
import time as _time

import numpy as np
import pandas as pd
import requests

import config
import hedge_core as core
from strategies import strategy_hedge

TD_URL = "https://api.twelvedata.com/time_series"
MIN_TRADES_TRAIN = 30


# ---------- dati ----------
def fetch_history(pages):
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        raise SystemExit("TWELVE_DATA_API_KEY mancante.")
    frames, end = [], None
    for k in range(pages):
        params = {
            "symbol": config.SYMBOL, "interval": config.TIMEFRAME, "outputsize": 5000,
            "timezone": "UTC", "apikey": api_key,
        }
        if end:
            params["end_date"] = end
        data = requests.get(TD_URL, params=params, timeout=30).json()
        if data.get("status") == "error" or "values" not in data:
            print(f"Pagina {k + 1}: {data.get('code')} {data.get('message')}")
            break
        part = pd.DataFrame(data["values"])
        part["datetime"] = pd.to_datetime(part["datetime"])
        frames.append(part)
        end = (part["datetime"].min() - pd.Timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
        print(f"Pagina {k + 1}/{pages}: {len(part)} candele fino a {part['datetime'].min()}")
        if k < pages - 1:
            _time.sleep(8)  # limite piano gratuito: 8 richieste/minuto
    if not frames:
        raise SystemExit("Nessun dato scaricato.")
    return clean(pd.concat(frames))


def clean(df):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.drop_duplicates("datetime").set_index("datetime").sort_index()
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    now_utc = pd.Timestamp.now(tz="UTC").tz_localize(None)
    if len(df) and df.index[-1] + pd.Timedelta(minutes=core.CANDLE_MIN) > now_utc:
        df = df.iloc[:-1]
    return df[[c for c in ("open", "high", "low", "close", "volume") if c in df.columns]]


# ---------- contesto numerico (veloce) ----------
class Ctx:
    def __init__(self, df):
        self.df = df
        rome = df.index.tz_localize("UTC").tz_convert(config.TIMEZONE)
        self.o = df["open"].to_numpy()
        self.h = df["high"].to_numpy()
        self.l = df["low"].to_numpy()
        self.c = df["close"].to_numpy()
        self.day = (rome.year * 10000 + rome.month * 100 + rome.day).to_numpy()
        self.wd = rome.dayofweek.to_numpy()   # 0=lunedi ... 6=domenica (il live non lavora sab/dom)
        self.mins = (rome.hour * 60 + rome.minute).to_numpy()
        self.n = len(df)
        self.pos = {ts: i for i, ts in enumerate(df.index)}
        self.start_m = config.SIGNAL_START.hour * 60 + config.SIGNAL_START.minute
        self.end_m = config.SIGNAL_END.hour * 60 + config.SIGNAL_END.minute
        self.close_m = config.FORCE_CLOSE.hour * 60 + config.FORCE_CLOSE.minute

    def signal_ok(self, i):
        end_m = self.mins[i] + core.CANDLE_MIN  # la candela chiude 5 minuti dopo l'inizio
        return self.wd[i] < 5 and self.start_m <= end_m < self.end_m


def run_trade(ctx, i, loser, entry):
    """Stesse regole del live. Parte dalla candela successiva al segnale."""
    for j in range(i + 1, ctx.n):
        if ctx.day[j] != ctx.day[i] or ctx.mins[j] >= ctx.close_m:
            exit_price = ctx.o[j] if ctx.day[j] == ctx.day[i] else ctx.c[j - 1]
            return {"i": i, "exit_i": j, "loser": loser, "result": "CHIUSURA", "slip": False,
                    "pnl": core.pnl_usd(loser, entry, exit_price)}
        outcome, slip, _ = core.step_outcome(loser, entry, ctx.h[j], ctx.l[j])
        if outcome:
            pnl = -config.SL_USD if outcome == "SL" else config.TP_USD  # AMBIGUO = caso peggiore
            return {"i": i, "exit_i": j, "loser": loser, "result": outcome, "slip": slip, "pnl": pnl}
    return None  # i dati finiscono prima dell'esito


def simulate(ctx, signals, max_per_day=None, overlap=False):
    max_per_day = config.MAX_SIGNALS_PER_DAY if max_per_day is None else max_per_day
    trades, last_exit, per_day = [], -1, {}
    for ts, loser, price in signals:
        i = ctx.pos[ts]
        if (i <= last_exit and not overlap) or not ctx.signal_ok(i):
            continue
        d = ctx.day[i]
        if max_per_day and per_day.get(d, 0) >= max_per_day:
            continue
        t = run_trade(ctx, i, loser, price)
        if t is None:
            continue
        per_day[d] = per_day.get(d, 0) + 1
        last_exit = t["exit_i"]
        trades.append(t)
    return trades


def baseline(ctx, start_i=0, end_i=None, step=12):
    """Ingressi 'ciechi' ogni 12 candele, entrambe le direzioni, stesse regole di uscita."""
    end_i = ctx.n if end_i is None else end_i
    trades = []
    for i in range(max(start_i, strategy_hedge.MIN_BARS), end_i, step):
        if not ctx.signal_ok(i):
            continue
        for loser in ("BUY", "SELL"):
            t = run_trade(ctx, i, loser, ctx.c[i])
            if t:
                trades.append(t)
    return trades


# ---------- statistiche ----------
def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def summarize(trades):
    n = len(trades)
    c = {k: sum(1 for t in trades if t["result"] == k) for k in ("SL", "TP", "AMBIGUO", "CHIUSURA")}
    decided = c["SL"] + c["TP"] + c["AMBIGUO"]
    lo, hi = wilson(c["SL"], decided)
    return {
        "n": n, **c, "decided": decided,
        "sl_rate": c["SL"] / decided if decided else 0.0,
        "ci": (lo, hi),
        "slip": sum(1 for t in trades if t["slip"]),
        "pnl_loser": sum(t["pnl"] for t in trades),
    }


def line(label, s):
    if s["n"] == 0:
        return f"{label}: nessun trade"
    return (f"{label}: {s['n']} trade | SL {s['SL']} TP {s['TP']} ambigui {s['AMBIGUO']} chiusura {s['CHIUSURA']} | "
            f"SL-first {s['sl_rate']*100:.1f}% (IC95 {s['ci'][0]*100:.1f}-{s['ci'][1]*100:.1f}) | "
            f"slippage oltre limite: {s['slip']} | P&L perdente {core.fmt_usd(s['pnl_loser'], True)}")


# ---------- vista giornaliera (obiettivo: almeno un SL al giorno) ----------
def daily_view(ctx, trades):
    """Giorni di mercato (finestra segnali) in cui lo SL virtuale viene toccato almeno una volta.

    I giorni senza alcun segnale contano come obiettivo mancato.
    """
    all_days = {int(ctx.day[i]) for i in range(ctx.n) if ctx.signal_ok(i)}
    by_day = {}
    for t in trades:
        by_day.setdefault(int(ctx.day[t["i"]]), []).append(t)
    days = len(all_days)
    hit = sum(1 for ts in by_day.values() if any(t["result"] == "SL" for t in ts))
    ge = sum(1 for ts in by_day.values() if len(ts) >= config.TARGET_SIGNALS_PER_DAY)
    n_sig = sum(len(v) for v in by_day.values())
    real = -sum(t["pnl"] for t in trades) * config.MIRROR_LOT_RATIO
    lo, hi = wilson(hit, days)
    return {"days": days, "hit": hit, "rate": hit / days if days else 0.0, "ci": (lo, hi),
            "real": real, "avg_sig": n_sig / days if days else 0.0, "ge_target": ge}


def daily_line(label, d):
    if d["days"] == 0:
        return f"{label}: nessun giorno di mercato"
    return (f"{label}: {d['days']} giorni | SL raggiunto in {d['hit']} "
            f"({d['rate']*100:.0f}%, IC95 {d['ci'][0]*100:.0f}-{d['ci'][1]*100:.0f}) | "
            f"segnali/giorno {d['avg_sig']:.1f}, giorni con >={config.TARGET_SIGNALS_PER_DAY}: {d['ge_target']} | "
            f"P&L speculare reale (lotti x{config.MIRROR_LOT_RATIO:g}) {core.fmt_usd(d['real'], True)}")


def blind_signals(ctx, step=36, seed=0):
    """Segnali 'ciechi' (direzione casuale) per un riferimento giornaliero onesto.
    step=36 candele = uno ogni 3 ore, cioe' circa 4-5 al giorno: stessa quantita' di tentativi."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(strategy_hedge.MIN_BARS, ctx.n, step):
        if ctx.signal_ok(i):
            out.append((ctx.df.index[i], "BUY" if rng.random() < 0.5 else "SELL", ctx.c[i]))
    return out


def paced_signals(ctx, df, params=None, start_i=0):
    """Replica ESATTA della logica live: ritmo target, livelli di rilassamento, distanza minima, tetto."""
    frames = [strategy_hedge.level_frame(df, lvl, params) for lvl in (0, 1, 2)]
    losers = [f["loser"].to_numpy() for f in frames]
    out, levels, per_day, last_i = [], {}, {}, {}
    gap_candles = -(-config.MIN_SIGNAL_GAP_MIN // core.CANDLE_MIN)
    for i in range(max(start_i, strategy_hedge.MIN_BARS), ctx.n):
        if not ctx.signal_ok(i):
            continue
        d = int(ctx.day[i])
        n = per_day.get(d, 0)
        if config.MAX_SIGNALS_PER_DAY and n >= config.MAX_SIGNALS_PER_DAY:
            continue
        if i - last_i.get(d, -10**9) < gap_candles:
            continue
        top = core.max_relax_level(n, int(ctx.mins[i]) + core.CANDLE_MIN)
        for lvl in range(top + 1):
            if losers[lvl][i]:
                ts = df.index[i]
                out.append((ts, losers[lvl][i], ctx.c[i]))
                levels[ts] = lvl
                per_day[d] = n + 1
                last_i[d] = i
                break
    return out, levels


# ---------- una posizione alla volta ----------
def sequential_trades(ctx, df, params=None, blind=False, seed=0):
    """Replica del live con SINGLE_POSITION: un solo trade aperto, stop del giorno dopo uno SL,
    nuovo tentativo solo dopo TP / chiusura, distanza minima e tetto giornaliero.
    blind=True: stessi vincoli ma direzione a caso e ingresso appena si puo' (riferimento)."""
    import random
    rng = random.Random(seed)
    frames = [strategy_hedge.level_frame(df, lvl, params) for lvl in (0, 1, 2)]
    losers = [f["loser"].to_numpy() for f in frames]
    gap_candles = -(-config.MIN_SIGNAL_GAP_MIN // core.CANDLE_MIN)
    trades, busy_until, per_day, last_i, done = [], -1, {}, {}, set()
    for i in range(max(0, strategy_hedge.MIN_BARS), ctx.n):
        if i < busy_until or not ctx.signal_ok(i):
            continue
        last = getattr(config, "LAST_SIGNAL_TIME", None)
        if last is not None and ctx.mins[i] + core.CANDLE_MIN > last.hour * 60 + last.minute:
            continue
        d = int(ctx.day[i])
        n = per_day.get(d, 0)
        if d in done or (config.MAX_SIGNALS_PER_DAY and n >= config.MAX_SIGNALS_PER_DAY):
            continue
        if i - last_i.get(d, -10**9) < gap_candles:
            continue
        loser = None
        if blind:
            loser = rng.choice(("BUY", "SELL"))
        else:
            top = core.max_relax_level(n, int(ctx.mins[i]) + core.CANDLE_MIN)
            for lvl in range(top + 1):
                if losers[lvl][i]:
                    loser = losers[lvl][i]
                    break
        if not loser:
            continue
        t = run_trade(ctx, i, loser, ctx.c[i])
        if t is None:
            continue
        per_day[d] = n + 1
        last_i[d] = i
        busy_until = t["exit_i"]
        t["n"] = n + 1
        trades.append(t)
        if config.STOP_AFTER_EXECUTION or t["result"] == "SL":
            done.add(d)  # regola attuale: primo trade eseguito e basta. Con STOP_AFTER_EXECUTION=False (solo what-if): stop dopo lo SL, nuovo tentativo dopo TP/chiusura
    return trades


def run_sequential(ctx, df, label, overrides, blind=False):
    saved = {k: getattr(config, k) for k in overrides}
    for k, v in overrides.items():
        setattr(config, k, v)
    try:
        tr = sequential_trades(ctx, df, blind=blind)
    finally:
        for k, v in saved.items():
            setattr(config, k, v)
    d, sm = daily_view(ctx, tr), summarize(tr)
    first = [t for t in tr if t["n"] == 1]
    first_sl = sum(1 for t in first if t["result"] == "SL")
    print(f"   {label}: SL in {d['hit']}/{d['days']} giorni ({d['rate']*100:.0f}%, IC95 {d['ci'][0]*100:.0f}-{d['ci'][1]*100:.0f}) | "
          f"{d['avg_sig']:.1f} trade/giorno | SL gia' al 1o tentativo {first_sl}/{d['days']} giorni | "
          f"TP/giorno {sm['TP']/max(d['days'],1):.1f} | P&L speculare reale {core.fmt_usd(d['real'], True)}")


SEQ_VARIANTS = [
    ("config attuale (filtri selettivi, ultimo segnale 15:00)", {}),
    ("filtri allargati (base 1)", dict(BASE_RELAX_LEVEL=1)),
    ("ultimo segnale alle 14:00", dict(LAST_SIGNAL_TIME=time(14, 0))),
    ("ultimo segnale alle 16:00", dict(LAST_SIGNAL_TIME=time(16, 0))),
    ("ultimo segnale alle 20:00 (nessun limite)", dict(LAST_SIGNAL_TIME=time(20, 0))),
    ("WHAT-IF: 2 tentativi (il secondo solo dopo un TP)", dict(STOP_AFTER_EXECUTION=False, MAX_SIGNALS_PER_DAY=2)),
    ("WHAT-IF: 3 tentativi (il successivo solo dopo un TP)", dict(STOP_AFTER_EXECUTION=False, MAX_SIGNALS_PER_DAY=3)),
]


# ---------- varianti operative ----------
def max_open(trades):
    ev = sorted([(t["i"], 1) for t in trades] + [(t["exit_i"], -1) for t in trades])
    cur = best = 0
    for _, delta in ev:
        cur += delta
        best = max(best, cur)
    return best


def run_variant(ctx, df, label, overrides, opposite=False):
    """Cambia solo parametri di ESECUZIONE (non gli indicatori) e rilegge il risultato giornaliero."""
    saved = {k: getattr(config, k) for k in overrides}
    for k, v in overrides.items():
        setattr(config, k, v)
    try:
        sg, _ = paced_signals(ctx, df)
        if opposite:  # per ogni segnale apre anche la direzione opposta nello stesso istante
            sg = sg + [(ts, core.opposite(loser), price) for ts, loser, price in sg]
        tr = simulate(ctx, sg, overlap=True, max_per_day=0 if opposite else None)
    finally:
        for k, v in saved.items():
            setattr(config, k, v)
    d, sm = daily_view(ctx, tr), summarize(tr)
    print(f"   {label}: SL in {d['hit']}/{d['days']} giorni ({d['rate']*100:.0f}%, IC95 {d['ci'][0]*100:.0f}-{d['ci'][1]*100:.0f}) | "
          f"{d['avg_sig']:.1f} trade/giorno | max aperti insieme {max_open(tr)} | TP/giorno {sm['TP']/max(d['days'],1):.1f} | "
          f"P&L speculare reale {core.fmt_usd(d['real'], True)}")


VARIANTS = [
    ("attuale (base 0, target 4, tetto 8, distanza 20')", {}, False),
    ("piu' tentativi (base 1, 8, 20, 10')", dict(BASE_RELAX_LEVEL=1, TARGET_SIGNALS_PER_DAY=8, MAX_SIGNALS_PER_DAY=20, MIN_SIGNAL_GAP_MIN=10), False),
    ("distanziati 60' (base 1, 4, 8)", dict(BASE_RELAX_LEVEL=1, MIN_SIGNAL_GAP_MIN=60), False),
    ("distanziati 120' (base 1, 4, 6)", dict(BASE_RELAX_LEVEL=1, MAX_SIGNALS_PER_DAY=6, MIN_SIGNAL_GAP_MIN=120), False),
    ("coppie opposte (come attuale, ogni segnale + il contrario)", {}, True),
]


# ---------- ottimizzazione ----------
COMPARE = {
    "trend-pullback": {"mode": "trend", "trigger": "pullback"},
    "trend-breakout": {"mode": "trend", "trigger": "breakout"},
    "range-VWAP": {"mode": "reversion"},
    "adattiva-pullback": {"mode": "adaptive", "trigger": "pullback"},
    "adattiva-breakout": {"mode": "adaptive", "trigger": "breakout"},
}

GRID = {
    "trigger": ["pullback", "breakout"],
    "er_trend_min": [0.20, 0.30],
    "er_range_max": [0.08, 0.12, 0.16],
    "vwap_dev_k": [1.5, 2.0, 2.5],
    "body_atr_min": [0.4, 0.6],
    "atr_min": [2.5, 3.5],
}


def optimize(df, ctx, mode="adaptive"):
    split = int(ctx.n * 0.7)
    keys = list(GRID)
    results = []
    tested = 0
    for combo in itertools.product(*GRID.values()):
        params = dict(zip(keys, combo))
        params["mode"] = mode
        tested += 1
        sigs = [s for s in strategy_hedge.run(df, params) if ctx.pos[s[0]] < split]
        s = summarize(simulate(ctx, sigs))
        if s["decided"] >= MIN_TRADES_TRAIN:
            results.append((s["ci"][0], params, s))
    if not results:
        print("Nessuna combinazione con abbastanza trade in addestramento: servono piu' dati (--pages).")
        return None
    results.sort(key=lambda r: r[0], reverse=True)
    print(f"\n{tested} combinazioni provate: piu' se ne provano, piu' il migliore e' frutto del caso.")
    print(f"Migliori 5 in addestramento (primo 70% dei dati, ordinati per limite inferiore IC95):")
    for _, params, s in results[:5]:
        print(" ", params)
        print("   ", line("train", s))

    best = results[0][1]
    test_sigs = [s for s in strategy_hedge.run(df, best) if ctx.pos[s[0]] >= split]
    test_trades = simulate(ctx, test_sigs)
    test = summarize(test_trades)
    base_test = summarize(baseline(ctx, start_i=split))
    print("\n=== VERIFICA FUORI CAMPIONE (ultimo 30%, mai visto in ottimizzazione) ===")
    print("Parametri scelti:", best)
    print(line("strategia", test))
    print(line("ingresso cieco", base_test))
    return best, test, base_test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=4, help="pagine da 5000 candele M5 (circa 17 giorni di mercato l'una)")
    ap.add_argument("--csv", type=str, help="CSV con datetime,open,high,low,close (UTC) al posto di Twelve Data")
    ap.add_argument("--optimize", action="store_true")
    ap.add_argument("--mode", default="adaptive", choices=["adaptive", "trend", "reversion"],
                    help="modalita' da ottimizzare con --optimize")
    args = ap.parse_args()

    df = clean(pd.read_csv(args.csv)) if args.csv else fetch_history(args.pages)
    ctx = Ctx(df)
    print(f"\nDati: {len(df)} candele M5 dal {df.index[0]} al {df.index[-1]} (UTC)")
    print(f"Parametri: SL {config.SL_USD:.0f}$ ({config.SL_POINTS:.2f} pt) | TP {config.TP_USD:.0f}$ "
          f"({config.TP_POINTS:.2f} pt) | slippage max {config.SLIPPAGE_MAX_USD:.0f}$ | "
          f"finestra {config.SIGNAL_START:%H:%M}-{config.SIGNAL_END:%H:%M} | chiusura {config.FORCE_CLOSE:%H:%M}")

    has_vol = "volume" in df.columns and df["volume"].fillna(0).nunique() > 1
    print(f"Volumi nel feed: {'si (VWAP ponderato)' if has_vol else 'no (VWAP = media di prezzo di sessione)'}")

    print("\n=== CONFRONTO MODALITA' (parametri di default, tutti i dati) ===")
    for name, over in COMPARE.items():
        tr = simulate(ctx, strategy_hedge.run(df, over))
        print(line(name, summarize(tr)))
        print("   ", daily_line("obiettivo giornaliero", daily_view(ctx, tr)))
    print(line("ingresso cieco", summarize(baseline(ctx))))

    print("\n=== UN SOLO TRADE AL GIORNO (si esegue il primo segnale, poi basta qualunque esito) ===")
    for label, over in SEQ_VARIANTS:
        run_sequential(ctx, df, label, over)
    run_sequential(ctx, df, "riferimento cieco (direzione a caso)", dict(), blind=True)
    print("   Poche giornate: differenze di pochi punti sono rumore. Se i segnali non battono il riferimento cieco, il vantaggio e' solo il numero di tentativi.")
    print("Soglia teorica ingresso cieco: "
          f"{config.TP_POINTS / (config.TP_POINTS + config.SL_POINTS) * 100:.1f}% SL-first")

    if args.optimize:
        optimize(df, ctx, args.mode)
    print("\nNota: il risultato in campione e' ottimistico. Vale solo la verifica fuori campione, "
          "e solo se l'intervallo di confidenza sta chiaramente sopra l'ingresso cieco.")


if __name__ == "__main__":
    main()
