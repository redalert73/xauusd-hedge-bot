# ==========================================
# TEST TIMESTRAL - la previsione del modello porta lo SL per primo sopra il caso?
# ==========================================
# Per ogni candela (ogni 30 min, dentro la finestra segnali) il modello legge le ultime N chiusure M5 e
# prevede l'andamento delle prossime ore. Se prevede prezzo in salita, la gamba PERDENTE e' SELL (lo SL si tocca
# se il prezzo sale); se prevede discesa, e' BUY. Si confronta con la base a caso sugli stessi istanti.
# Nessun parametro viene ottimizzato: orizzonte e contesto sono fissati prima del test.
#
# Uso: python timestral_test.py --pages 20 --model mistralai/Timestral-5M

import argparse
import math
import time as _time
from datetime import time

import numpy as np
import pandas as pd

import config
from backtest_hedge import Ctx, clean, fetch_history, run_trade, wilson
from strategies import strategy_hedge

THEORY = config.TP_POINTS / (config.TP_POINTS + config.SL_POINTS)


def load_forecaster(name):
    try:
        from timestral import TimestralForecaster
    except ImportError as e:
        raise SystemExit("Manca il pacchetto: pip install timecopilot-timestral (serve anche torch)") from e
    return TimestralForecaster.from_pretrained(name)


def forecast_batch(fc, ctxs, horizon):
    """ctxs: array (B, T). Ritorna (mediana (B,H), quantili (B,H,Q))."""
    out = fc.forecast(np.asarray(ctxs, dtype=np.float32), prediction_length=horizon)
    med = np.asarray(out.median)
    q = np.asarray(out.quantiles)
    med = med.reshape(len(ctxs), -1, med.shape[-1])[:, 0, :]          # (B, H) con 1 variata
    q = q.reshape(len(ctxs), -1, q.shape[-2], q.shape[-1])[:, 0]      # (B, H, Q)
    return med, q


def rate_line(name, a, base):
    n = len(a)
    if n == 0:
        return f"  {name:46s} | nessun caso"
    k = int(np.sum(a))
    lo, hi = wilson(k, n)
    z = (k / n - base) / math.sqrt(max(base * (1 - base) / n, 1e-12))
    return (f"  {name:46s} | SL per primo {k/n*100:5.1f}% su {n:4d} (IC95 {lo*100:.0f}-{hi*100:.0f}) | "
            f"base a caso {base*100:.1f}% | scarto {z:+.1f} sigma")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=20)
    ap.add_argument("--csv", type=str)
    ap.add_argument("--model", type=str, default="mistralai/Timestral-5M")
    ap.add_argument("--context", type=int, default=512, help="candele M5 date al modello")
    ap.add_argument("--horizon", type=int, default=24, help="candele M5 previste (24 = 2 ore)")
    ap.add_argument("--step", type=int, default=6, help="un campione ogni N candele (6 = 30 minuti)")
    ap.add_argument("--max-samples", type=int, default=6000)
    ap.add_argument("--batch", type=int, default=32)
    args = ap.parse_args()

    df = clean(pd.read_csv(args.csv)) if args.csv else fetch_history(args.pages)
    ctx = Ctx(df)
    last_m = config.LAST_SIGNAL_TIME.hour * 60 + config.LAST_SIGNAL_TIME.minute
    idx = [i for i in range(max(args.context, strategy_hedge.MIN_BARS), ctx.n, args.step)
           if ctx.signal_ok(i) and ctx.mins[i] + 5 <= last_m]
    if len(idx) > args.max_samples:
        idx = idx[-args.max_samples:]
    c = ctx.c
    tr = np.maximum(ctx.h - ctx.l, np.maximum(np.abs(ctx.h - np.r_[c[0], c[:-1]]), np.abs(ctx.l - np.r_[c[0], c[:-1]])))
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()

    print(f"Dati: {len(df)} candele M5 | campioni: {len(idx)} | modello {args.model} | contesto {args.context} | orizzonte {args.horizon} candele")
    fc = load_forecaster(args.model)

    recs = []
    t0 = _time.time()
    for b in range(0, len(idx), args.batch):
        part = idx[b:b + args.batch]
        X = np.stack([c[i - args.context + 1:i + 1] for i in part])
        med, q = forecast_batch(fc, X, args.horizon)
        for k, i in enumerate(part):
            last = c[i]
            s = (med[k, -1] - last) / atr[i]                    # previsione a fine orizzonte, in ATR
            pup = float(np.mean(q[k, -1, :] > last))            # quota di quantili sopra il prezzo attuale
            res = {}
            for side in ("BUY", "SELL"):
                t = run_trade(ctx, i, side, last)
                res[side] = None if t is None else (1 if t["result"] == "SL" else 0)
            if res["BUY"] is None or res["SELL"] is None:
                continue
            fut = c[i + args.horizon] - last if i + args.horizon < ctx.n else np.nan
            recs.append((i, s, pup, res["BUY"], res["SELL"], fut / atr[i]))
        if (b // args.batch) % 20 == 0:
            print(f"  {b + len(part)}/{len(idx)} campioni, {(_time.time() - t0)/60:.1f} min", flush=True)

    R = pd.DataFrame(recs, columns=["i", "s", "pup", "sl_buy", "sl_sell", "fut"])
    if R.empty:
        raise SystemExit("Nessun campione valido.")
    R["pred_loser_sl"] = np.where(R["s"] > 0, R["sl_sell"], R["sl_buy"])      # previsto su: perdente SELL
    R["base"] = (R["sl_buy"] + R["sl_sell"]) / 2
    base = float(R["base"].mean())

    print(f"\nCampioni validi: {len(R)} | dal {df.index[0]} al {df.index[-1]} (UTC)")
    print(f"Base a caso (media BUY/SELL perdente sugli stessi istanti): {base*100:.1f}% | teorico {THEORY*100:.1f}%")
    ok = R.dropna(subset=["fut"])
    hit = float(np.mean(np.sign(ok["s"]) == np.sign(ok["fut"])))
    lo, hi = wilson(int(round(hit * len(ok))), len(ok))
    print(f"Direzione prevista giusta (a {args.horizon} candele): {hit*100:.1f}% (IC95 {lo*100:.1f}-{hi*100:.1f}) su {len(ok)} | 50% = caso")

    print("\nESITO SULLO SL (scegliendo la gamba perdente secondo il modello):")
    print(rate_line("tutti i campioni", R["pred_loser_sl"], base))
    cut = int(len(R) * 0.6)
    print(rate_line("primo 60% (storia piu' vecchia)", R["pred_loser_sl"][:cut], float(R["base"][:cut].mean())))
    print(rate_line("ultimo 40% (storia piu' recente)", R["pred_loser_sl"][cut:], float(R["base"][cut:].mean())))
    for pct in (50, 25):
        thr = R["s"].abs().quantile(1 - pct / 100)
        m = R["s"].abs() >= thr
        print(rate_line(f"solo il {pct}% con previsione piu' forte", R["pred_loser_sl"][m], float(R["base"][m].mean())))
    conv = (R["pup"] >= 0.8) | (R["pup"] <= 0.2)
    print(rate_line("solo previsioni decise (>=80% o <=20% quantili)", R["pred_loser_sl"][conv], float(R["base"][conv].mean())))
    inv = np.where(R["s"] > 0, R["sl_buy"], R["sl_sell"])
    print(rate_line("CONTRARIO (perdente opposta alla previsione)", pd.Series(inv), base))

    print("\nPer orario di ingresso (ora italiana), esito con la previsione:")
    R["h"] = ctx.mins[R["i"].to_numpy()] // 60
    for hh, g in R.groupby("h"):
        print(rate_line(f"{int(hh):02d}:00", g["pred_loser_sl"], float(g["base"].mean())))

    print("\nCome leggere: il modello e' utile solo se 'tutti', 'ultimo 40%' e 'solo previsioni forti' stanno chiaramente sopra la base")
    print("(scarto di almeno +3 sigma e IC95 sopra la base) e la direzione prevista giusta e' sopra il 50% con IC lontano dal caso.")
    print("Una sola riga positiva tra molte e' probabilmente fortuna. Se non regge, il modello non aggiunge nulla.")


if __name__ == "__main__":
    main()
