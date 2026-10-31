# ==========================================
# EDGE SCAN - esiste una condizione che porta lo SL per primo molto sopra il 47,6%?
# ==========================================
# Per ogni candela (ogni 15 min in finestra) calcola se la gamba PERDENTE, aperta in BUY o in SELL,
# tocca prima lo SL. Poi cerca le condizioni (ora, trend, volatilita', RSI, distanza dal VWAP...)
# in cui una direzione va in SL piu' spesso, scelte sul 60% PIU' VECCHIO dei dati e verificate
# sul 40% PIU' RECENTE (mai visto). Se fuori campione non regge, e' rumore.
#
# Uso: python edge_scan.py --pages 6        (o --csv file.csv)

import argparse
import math

import numpy as np
import pandas as pd

import config
import hedge_core as core
from backtest_hedge import Ctx, clean, fetch_history, run_trade, wilson
from strategies import strategy_hedge

STEP = 3            # una candela ogni 15 minuti
MIN_N = 60          # campioni minimi per condizione, in campione
THEORY = config.TP_POINTS / (config.TP_POINTS + config.SL_POINTS)


def build(df, ctx):
    p = strategy_hedge._merge(None)
    c, h, l, o = df["close"], df["high"], df["low"], df["open"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    ema10, ema20, ema100 = (c.ewm(span=s, adjust=False).mean() for s in (10, 20, 100))
    vwap, _ = strategy_hedge.session_vwap(df, p)
    er = strategy_hedge.efficiency_ratio(c, 48)
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rsi = (100 - 100 / (1 + up / dn)).fillna(50)
    atr_med = atr.rolling(864, min_periods=288).median()
    # ---- livelli di prezzo: range del giorno precedente (di mercato), Fibonacci, massimi/minimi di oggi, numeri tondi ----
    day = pd.Series(ctx.day, index=df.index)
    wk = pd.Series(ctx.wd < 5, index=df.index)
    daily = pd.DataFrame({"h": h[wk], "l": l[wk], "d": day[wk]}).groupby("d").agg(h=("h", "max"), l=("l", "min"))
    prev = daily.shift(1)
    pdh = day.map(prev["h"])
    pdl = day.map(prev["l"])
    rng_prev = (pdh - pdl).replace(0, np.nan)
    pos_prev = (c - pdl) / rng_prev                       # 0 = minimo di ieri, 1 = massimo di ieri
    fibs = np.array([0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0])
    fib_dist = pd.Series(np.min(np.abs(pos_prev.to_numpy()[:, None] - fibs[None, :]), axis=1), index=df.index) * rng_prev / atr
    day_hi = h.groupby(day).cummax()
    day_lo = l.groupby(day).cummin()
    round50 = (c / 50).round() * 50

    F = pd.DataFrame(index=df.index)
    F["posizione nel range di ieri (0=min,1=max)"] = pos_prev
    F["distanza dal Fibonacci di ieri piu' vicino (in ATR)"] = fib_dist
    F["distanza dal massimo di ieri (in ATR)"] = (c - pdh) / atr
    F["distanza dal minimo di ieri (in ATR)"] = (c - pdl) / atr
    F["distanza dal massimo di oggi (in ATR)"] = (c - day_hi) / atr
    F["distanza dal minimo di oggi (in ATR)"] = (c - day_lo) / atr
    F["distanza dal numero tondo 50 (in ATR, con segno)"] = (c - round50) / atr
    F["ora"] = (ctx.mins // 120) * 2                       # blocchi da 2 ore (ora italiana)
    F["trend EMA10-EMA20 (in ATR)"] = (ema10 - ema20) / atr
    F["prezzo vs EMA100 (in ATR)"] = (c - ema100) / atr
    F["prezzo vs VWAP (in ATR)"] = (c - vwap) / atr
    F["rendimento 6 candele (in ATR)"] = (c - c.shift(6)) / atr
    F["rendimento 24 candele (in ATR)"] = (c - c.shift(24)) / atr
    F["corpo ultima candela (in ATR)"] = (c - o) / atr
    F["RSI"] = rsi
    F["efficiency ratio"] = er
    F["ATR / ATR mediano"] = atr / atr_med
    return F


def buckets(F, train_idx):
    """Condizioni: per ora valori esatti, per le altre i terzili calcolati SOLO sul periodo di scelta."""
    out = []
    for col in F.columns:
        if col == "ora":
            for v in sorted(F[col].dropna().unique()):
                out.append((f"ora {int(v):02d}-{int(v)+2:02d}", (F[col] == v).to_numpy()))
            continue
        q1, q2 = F[col].iloc[train_idx].quantile([1 / 3, 2 / 3])
        x = F[col].to_numpy()
        out.append((f"{col}: basso", x <= q1))
        out.append((f"{col}: medio", (x > q1) & (x <= q2)))
        out.append((f"{col}: alto", x > q2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=6)
    ap.add_argument("--csv", type=str)
    args = ap.parse_args()
    df = clean(pd.read_csv(args.csv)) if args.csv else fetch_history(args.pages)
    ctx = Ctx(df)
    F = build(df, ctx)

    idx = [i for i in range(strategy_hedge.MIN_BARS, ctx.n, STEP) if ctx.signal_ok(i)]
    res = {"BUY": {}, "SELL": {}}
    full = {}
    for i in idx:
        for side in ("BUY", "SELL"):
            t = run_trade(ctx, i, side, ctx.c[i])
            if t:
                res[side][i] = 1 if t["result"] == "SL" else 0
                full.setdefault(int(ctx.mins[i] // 60), []).append(t["result"])
    idx = [i for i in idx if i in res["BUY"] and i in res["SELL"]]
    cut = int(len(idx) * 0.6)
    train, test = np.array(idx[:cut]), np.array(idx[cut:])
    print(f"\nCampioni: {len(idx)} candele ({len(train)} per scegliere, {len(test)} per verificare) | "
          f"dal {df.index[0]} al {df.index[-1]} (UTC)")
    for side in ("BUY", "SELL"):
        a = np.array([res[side][i] for i in idx])
        lo, hi = wilson(int(a.sum()), len(a))
        print(f"Base {side} perdente: SL per primo {a.mean()*100:.1f}% (IC95 {lo*100:.1f}-{hi*100:.1f}) | teorico a caso {THEORY*100:.1f}%")

    print("\nPER ORA DI INGRESSO (ora italiana), entrambe le direzioni, tutti i dati:")
    print("  ora  | prove | SL per primo | TP per primo | ne' SL ne' TP (chiusura 21:45) | range medio candela (pt)")
    atr_h = F["ATR / ATR mediano"]
    for hh in sorted(full):
        r = full[hh]
        n = len(r)
        sl, tp = r.count("SL") / n * 100, r.count("TP") / n * 100
        rest = 100 - sl - tp
        atr_pts = np.nanmean([df["high"].iloc[i] - df["low"].iloc[i] for i in idx if ctx.mins[i] // 60 == hh])
        print(f"  {hh:02d}:00 | {n:5d} | {sl:11.1f}% | {tp:11.1f}% | {rest:29.1f}% | {atr_pts:6.2f}")
    # ore in cui lo SL per primo e' STATISTICAMENTE sotto la media generale (limite superiore IC95 < media)
    tot = [x for r in full.values() for x in r]
    overall = tot.count("SL") / len(tot)
    slow_h = []
    for hh in sorted(full):
        r = full[hh]
        if wilson(r.count("SL"), len(r))[1] < overall:
            slow_h.append(hh)
    print(f"  Media generale SL per primo: {overall*100:.1f}%. Ore sensibilmente sotto la media (IC95): "
          f"{', '.join(f'{h:02d}:00' for h in slow_h) or 'nessuna'}")
    if slow_h:
        wins, start = [], slow_h[0]
        for a_, b_ in zip(slow_h, slow_h[1:] + [None]):
            if b_ != a_ + 1:
                wins.append((start, a_ + 1))
                start = b_
        txt = ", ".join(f"(time({s_}, 0), time({e_}, 0))" for s_, e_ in wins)
        print(f"  Riga suggerita per config.py:  LOW_LIQUIDITY_WINDOWS = [{txt}]")
        print("  Attenzione: le ore serali risultano basse anche perche' resta poco tempo prima delle 21:45.")
    print("  Dove 'SL per primo' scende e la colonna 'ne' SL ne' TP' sale, il mercato e' troppo lento per toccare lo SL.")

    B = buckets(F, train)
    rows = []
    for name, mask in B:
        for side in ("BUY", "SELL"):
            tr_i = [i for i in train if mask[i]]
            if len(tr_i) < MIN_N:
                continue
            rate = np.mean([res[side][i] for i in tr_i])
            te_i = [i for i in test if mask[i]]
            k = int(sum(res[side][i] for i in te_i))
            rows.append((rate, name, side, len(tr_i), k, len(te_i)))
    rows.sort(reverse=True)
    print(f"\nCondizioni provate: {len(B) * 2} (piu' se ne provano, piu' ne escono 'belle' per puro caso)")
    print("Migliori 12 sul periodo di scelta, con la verifica sul periodo nuovo:")
    good = 0
    for rate, name, side, ntr, k, nte in rows[:12]:
        lo, hi = wilson(k, nte)
        ok = nte >= 40 and lo > 0.5
        good += ok
        print(f"  perdente {side:4s} | {name:40s} | scelta: {rate*100:4.1f}% su {ntr:4d} | "
              f"verifica: {(k/nte*100 if nte else 0):4.1f}% su {nte:4d} (IC95 {lo*100:.0f}-{hi*100:.0f}) {'<-- regge' if ok else ''}")
    print(f"\nCondizioni che reggono fuori campione (limite inferiore IC > 50%, almeno 40 casi): {good} su 12")
    print("Con tante condizioni provate, 1-2 'che reggono' possono essere fortuna: va riconfermata su altri mesi di dati.")
    print("Se nessuna regge, il vantaggio direzionale non c'e': lo SL per primo resta vicino al 47,6%.")


if __name__ == "__main__":
    main()
