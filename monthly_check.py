# ==========================================
# CONTROLLO MENSILE: l'oro si muove in range piu' stretti?
# ==========================================
# Per ogni mese: ampiezza media della giornata, SL per primo, TP per primo, trade non risolti alle 21:45.
# Poi confronta gli ultimi 3 mesi con i precedenti e prova SL piu' vicini (TP invariato).
# Uso: python monthly_check.py --pages 20

import argparse

import numpy as np
import pandas as pd

import config
from backtest_hedge import Ctx, clean, fetch_history, run_trade, wilson

STEP = 3          # un ingresso ogni 15 minuti
RECENT_MONTHS = 3


def sample(ctx, sl_usd=None):
    last = config.LAST_SIGNAL_TIME.hour * 60 + config.LAST_SIGNAL_TIME.minute
    out = []
    for i in range(300, ctx.n, STEP):
        if not ctx.signal_ok(i) or ctx.mins[i] + 5 > last:
            continue
        for side in ("BUY", "SELL"):
            t = run_trade(ctx, i, side, ctx.c[i], sl_usd)
            if t:
                out.append((i, t["result"]))
    return out


def rates(rows):
    n = len(rows)
    if not n:
        return 0, 0.0, 0.0, 0.0
    r = [x for _, x in rows]
    return n, r.count("SL") / n, r.count("TP") / n, r.count("CHIUSURA") / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=20)
    ap.add_argument("--csv", type=str)
    a = ap.parse_args()
    df = clean(pd.read_csv(a.csv)) if a.csv else fetch_history(a.pages)
    ctx = Ctx(df)
    month = df.index.to_period("M")

    wk = ctx.wd < 5
    g = pd.DataFrame({"d": ctx.day[wk], "h": ctx.h[wk], "l": ctx.l[wk], "m": month[wk].astype(str)})
    daily = g.groupby("d").agg(h=("h", "max"), l=("l", "min"), m=("m", "first"))
    daily["range"] = daily["h"] - daily["l"]

    rows = sample(ctx)
    by_m = {}
    for i, r in rows:
        by_m.setdefault(str(month[i]), []).append((i, r))

    print(f"\nDati dal {df.index[0]} al {df.index[-1]} (UTC) | SL {config.SL_USD:.0f}$ ({config.SL_POINTS:.2f} pt) | TP {config.TP_USD:.0f}$")
    print("\nPER MESE (ingressi ogni 15 min dalle 06:00 all'ultimo segnale, entrambe le direzioni)")
    print("  mese    | giorni | range medio giorno (pt) | SL per primo | TP per primo | non risolti")
    months = sorted(by_m)
    for m in months:
        n, sl, tp, cl = rates(by_m[m])
        d = daily[daily["m"] == m]
        print(f"  {m} | {len(d):6d} | {d['range'].mean():23.1f} | {sl*100:11.1f}% | {tp*100:11.1f}% | {cl*100:10.1f}%")

    recent = set(months[-RECENT_MONTHS:])
    old_rows = [x for m in months if m not in recent for x in by_m[m]]
    new_rows = [x for m in months if m in recent for x in by_m[m]]
    print(f"\nULTIMI {RECENT_MONTHS} MESI rispetto ai precedenti")
    for label, rr, ms in (("precedenti", old_rows, [m for m in months if m not in recent]), ("ultimi", new_rows, sorted(recent))):
        n, sl, tp, cl = rates(rr)
        lo, hi = wilson(int(round(sl * n)), n)
        rng = daily[daily["m"].isin(ms)]["range"].mean()
        print(f"  {label:10s}: range medio {rng:5.1f} pt | SL per primo {sl*100:4.1f}% (IC95 {lo*100:.1f}-{hi*100:.1f}) | non risolti {cl*100:4.1f}%")

    print("\nSL PIU' VICINI (TP invariato) negli ultimi mesi e nei precedenti")
    cut = min(i for i, _ in new_rows) if new_rows else ctx.n
    for sl_usd in (2000, 1800, 1500):
        rr = sample(ctx, float(sl_usd))
        o = [x for x in rr if x[0] < cut]
        n_ = [x for x in rr if x[0] >= cut]
        _, so, _, co = rates(o)
        _, sn, _, cn = rates(n_)
        print(f"  SL {sl_usd}$ ({sl_usd / config.USD_PER_POINT:.2f} pt): precedenti SL {so*100:4.1f}% non risolti {co*100:4.1f}% | "
              f"ultimi SL {sn*100:4.1f}% non risolti {cn*100:4.1f}%")
    print("\nCome leggere: se negli ultimi mesi il range medio e' sceso, lo SL per primo e' calato e i non risolti sono saliti,")
    print("l'oro si muove davvero meno: in quel caso uno SL piu' vicino puo' compensare. Se i numeri sono simili, non cambiare nulla.")


if __name__ == "__main__":
    main()
