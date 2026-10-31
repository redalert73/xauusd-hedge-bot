# ==========================================
# STRATEGIA HEDGE ADATTIVA - EMA 10/20/100 + VWAP + REGIME (M5)
# ==========================================
# La gamba SPECULARE e' quella che deve muoversi di 21.15 punti prima di
# tornare indietro di 19.23; la gamba PERDENTE e' sempre l'opposto.
#
# Adattamento al mercato (ricalcolato a ogni candela, quindi ogni giorno):
#   - REGIME via Efficiency Ratio (Kaufman) su 48 candele (4 ore):
#       ER alto  -> mercato direzionale -> modalita' TREND
#       ER basso -> mercato laterale    -> modalita' RANGE (ritorno al VWAP)
#       ER medio -> nessun segnale
#   - VOLATILITA' relativa: l'ATR corrente deve essere almeno il 70% della sua
#     mediana degli ultimi 3 giorni (oltre a un minimo assoluto per poter
#     percorrere ~21 punti). Le soglie su corpo/estensione sono multipli di ATR,
#     quindi si ridimensionano da sole nei giorni piu' calmi o piu' nervosi.
#   - VWAP di sessione ancorato a mezzanotte italiana (si azzera ogni giorno).
#     Se il feed non da' volumi (tipico per XAU/USD spot) i pesi sono uguali:
#     in quel caso e' la media di prezzo della sessione, non un VWAP vero.
#
# TREND (mirror in direzione del trend):
#   EMA10 > EMA20 > EMA100 e prezzo sopra VWAP (specchiato per SELL), RSI sano,
#   non troppo esteso dalla EMA10, e un trigger a scelta:
#     "pullback"  : chiusura che riprende la EMA10 dopo un ritracciamento
#                   rimasto sopra la EMA20
#     "breakout"  : rottura del massimo delle ultime N candele con candela decisa
# RANGE (mirror contro l'eccesso):
#   prezzo a >= k ATR dal VWAP, RSI estremo, candela di rientro, EMA100 piatta.
#
# I parametri sono un PUNTO DI PARTENZA: vanno verificati con
# backtest_hedge.py su dati reali prima di fidarsi.

import numpy as np
import pandas as pd

import config

DEFAULT_PARAMS = {
    "mode": "adaptive",        # "trend" | "reversion" | "adaptive"
    "trigger": "pullback",     # "pullback" | "breakout" (solo per la parte trend)
    "ema_fast": 10,
    "ema_mid": 20,
    "ema_trend": 100,
    "atr_period": 14,
    "rsi_period": 14,
    "er_period": 48,
    "er_trend_min": 0.25,
    "er_range_max": 0.12,
    "vwap_anchor_hour": 0,     # ora italiana a cui si azzera il VWAP
    "vwap_dev_k": 2.0,         # distanza dal VWAP in ATR per la parte range
    "min_session_bars": 24,    # candele minime nella sessione prima di fidarsi del VWAP
    "breakout_lookback": 6,
    "body_atr_min": 0.5,
    "close_pos_min": 0.70,
    "rsi_lo": 52,
    "rsi_hi": 72,
    "rsi_rev": 35,
    "atr_min": 3.0,
    "atr_ratio_min": 0.7,
    "atr_median_bars": 864,    # 3 giorni di candele M5
    "max_extension_atr": 1.5,
    "spike_range_atr": 3.0,
    "ema100_flat_atr": 0.5,    # pendenza massima EMA100 su 12 candele, in ATR (range)
}

MIN_BARS = 300  # sotto questa soglia ATR mediano ed EMA100 non sono affidabili

# Livello 1: stessi indicatori, soglie piu' larghe (entrambi i trigger).
RELAX1 = {
    "mode": "adaptive",
    "body_atr_min": 0.3,
    "er_trend_min": 0.15,
    "er_range_max": 0.20,
    "vwap_dev_k": 1.5,
    "atr_ratio_min": 0.5,
    "atr_min": 2.5,
}
# Livello 2 ("quota"): solo trend EMA10/EMA20 + lato del VWAP + candela concorde.
# Serve a garantire il ritmo dei segnali, NON ha alcun vantaggio statistico dimostrato.
LEVEL_NAMES = {0: "selettivo", 1: "esteso", 2: "quota"}


def _merge(params):
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    return p


def session_vwap(df, p):
    """VWAP ancorato all'ora italiana p['vwap_anchor_hour']; ritorna (vwap, candele_in_sessione)."""
    rome = df.index.tz_localize("UTC").tz_convert(config.TIMEZONE)
    key = (rome - pd.Timedelta(hours=p["vwap_anchor_hour"])).normalize().asi8
    tp = (df["high"] + df["low"] + df["close"]) / 3
    w = pd.Series(1.0, index=df.index)
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        if vol.sum() > 0 and vol.nunique() > 1:
            w = vol.where(vol > 0, np.nan).fillna(vol[vol > 0].median())
    num = (tp * w).groupby(key).cumsum()
    den = w.groupby(key).cumsum()
    n_in_session = pd.Series(1, index=df.index).groupby(key).cumsum()
    return num / den, n_in_session


def efficiency_ratio(c, n):
    change = (c - c.shift(n)).abs()
    path = c.diff().abs().rolling(n).sum()
    return change / path.replace(0, np.nan)


def features(df, params=None):
    """df: open/high/low/close (+ volume opzionale), indice = inizio candela UTC naive, tutte CHIUSE."""
    p = _merge(params)
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    ema_f = c.ewm(span=p["ema_fast"], adjust=False).mean()
    ema_m = c.ewm(span=p["ema_mid"], adjust=False).mean()
    ema_t = c.ewm(span=p["ema_trend"], adjust=False).mean()

    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / p["atr_period"], adjust=False).mean()
    atr_med = atr.rolling(p["atr_median_bars"], min_periods=288).median()

    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / p["rsi_period"], adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / p["rsi_period"], adjust=False).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rsi = 100 - 100 / (1 + up / dn)   # dn=0 -> inf -> RSI 100
    rsi = rsi.fillna(50.0)                # 0/0 (nessun movimento) -> neutro

    vwap, n_sess = session_vwap(df, p)
    er = efficiency_ratio(c, p["er_period"])

    rng = h - l
    body = (c - o).abs()
    close_pos = (c - l) / rng.replace(0, np.nan)
    dev = (c - vwap) / atr   # distanza dal VWAP in ATR

    # ---- filtri comuni ----
    common = (
        (atr >= p["atr_min"])
        & (atr >= p["atr_ratio_min"] * atr_med)
        & (rng <= p["spike_range_atr"] * atr)
        & (n_sess >= p["min_session_bars"])
        & pd.Series(np.arange(len(df)) >= MIN_BARS, index=df.index)
    )

    # ---- TREND ----
    lb = p["breakout_lookback"]
    prev_high = h.shift(1).rolling(lb).max()
    prev_low = l.shift(1).rolling(lb).min()
    if p["trigger"] == "breakout":
        trig_buy = (c > prev_high) & (c > o) & (body >= p["body_atr_min"] * atr) & (close_pos >= p["close_pos_min"])
        trig_sell = (c < prev_low) & (c < o) & (body >= p["body_atr_min"] * atr) & (close_pos <= 1 - p["close_pos_min"])
    else:  # pullback
        trig_buy = (c.shift(1) < ema_f.shift(1)) & (c.shift(1) > ema_m.shift(1)) & (c > ema_f) & (c > o) \
            & (body >= p["body_atr_min"] * atr)
        trig_sell = (c.shift(1) > ema_f.shift(1)) & (c.shift(1) < ema_m.shift(1)) & (c < ema_f) & (c < o) \
            & (body >= p["body_atr_min"] * atr)
    trend_buy = (
        (ema_f > ema_m) & (ema_m > ema_t) & (c > vwap) & trig_buy
        & rsi.between(p["rsi_lo"], p["rsi_hi"]) & ((c - ema_f) <= p["max_extension_atr"] * atr)
    )
    trend_sell = (
        (ema_f < ema_m) & (ema_m < ema_t) & (c < vwap) & trig_sell
        & rsi.between(100 - p["rsi_hi"], 100 - p["rsi_lo"]) & ((ema_f - c) <= p["max_extension_atr"] * atr)
    )

    # ---- RANGE (ritorno al VWAP) ----
    flat = (ema_t - ema_t.shift(12)).abs() <= p["ema100_flat_atr"] * atr
    rev_buy = (dev <= -p["vwap_dev_k"]) & (c > o) & (close_pos >= 0.65) & (rsi <= p["rsi_rev"]) & flat
    rev_sell = (dev >= p["vwap_dev_k"]) & (c < o) & (close_pos <= 0.35) & (rsi >= 100 - p["rsi_rev"]) & flat

    # ---- scelta del regime ----
    is_trend = er >= p["er_trend_min"]
    is_range = er <= p["er_range_max"]
    if p["mode"] == "quota":
        q_common = (
            (atr >= p["atr_min"]) & (rng <= p["spike_range_atr"] * atr) & (n_sess >= p["min_session_bars"])
            & pd.Series(np.arange(len(df)) >= MIN_BARS, index=df.index)
        )
        buy = q_common & (ema_f > ema_m) & (c > vwap) & (c > o)
        sell = q_common & (ema_f < ema_m) & (c < vwap) & (c < o)
        use_trend = pd.Series(True, index=df.index)
    elif p["mode"] == "trend":
        buy, sell = common & trend_buy, common & trend_sell
        use_trend = pd.Series(True, index=df.index)
    elif p["mode"] == "reversion":
        buy, sell = common & rev_buy, common & rev_sell
        use_trend = pd.Series(False, index=df.index)
    else:  # adaptive
        buy = common & ((is_trend & trend_buy) | (is_range & rev_buy))
        sell = common & ((is_trend & trend_sell) | (is_range & rev_sell))
        use_trend = is_trend

    out = pd.DataFrame(index=df.index)
    out["mirror"] = np.where(buy, "BUY", np.where(sell, "SELL", ""))
    out["loser"] = np.where(buy, "SELL", np.where(sell, "BUY", ""))
    out["regime"] = "QUOTA" if p["mode"] == "quota" else np.where(use_trend, "TREND", "RANGE")
    out["close"] = c
    out["atr"] = atr
    out["atr_ratio"] = atr / atr_med
    out["rsi"] = rsi
    out["er"] = er
    out["vwap"] = vwap
    return out


def run(df, params=None):
    """Tutti i segnali storici: lista di (inizio_candela, direzione_perdente, close)."""
    f = features(df, params)
    sig = f[f["loser"] != ""]
    return [(ts, r["loser"], r["close"]) for ts, r in sig.iterrows()]


def level_frame(df, level, params=None):
    """Segnali per livello di rilassamento (0/1/2). Al livello 1 si uniscono i due trigger."""
    base = dict(params or {})
    if level == 0:
        cfgs = [base]
    elif level == 1:
        cfgs = [{**base, **RELAX1, "trigger": t} for t in ("pullback", "breakout")]
    else:
        cfgs = [{**base, "mode": "quota"}]
    out = features(df, cfgs[0])
    for cfg in cfgs[1:]:
        f = features(df, cfg)
        mask = (out["loser"] == "") & (f["loser"] != "")
        out.loc[mask] = f.loc[mask]
    return _low_liquidity_filter(out)


def _low_liquidity_filter(out):
    """Nelle fasce LOW_LIQUIDITY_WINDOWS (ora IT) niente segnali se l'ATR e' sotto la soglia relativa (mercato lento)."""
    k = getattr(config, "LOW_LIQUIDITY_ATR_RATIO", 0)
    windows = getattr(config, "LOW_LIQUIDITY_WINDOWS", [])
    if not k or not windows or out.empty:
        return out
    rome = out.index.tz_localize("UTC").tz_convert(config.TIMEZONE)
    end_min = (rome.hour * 60 + rome.minute + 5).to_numpy()   # minuti a cui CHIUDE la candela
    in_win = np.zeros(len(out), dtype=bool)
    for start, end in windows:
        in_win |= (end_min > start.hour * 60 + start.minute) & (end_min <= end.hour * 60 + end.minute)
    slow = in_win & ~(out["atr_ratio"].to_numpy() >= k)      # NaN = non verificabile = bloccato
    out = out.copy()
    out.loc[slow, "loser"] = ""
    out.loc[slow, "mirror"] = ""
    return out


def check_last(df, params=None, relax=0):
    """Segnale sull'ULTIMA candela chiusa, provando i livelli 0..relax in ordine. None se assente."""
    if df is None or len(df) < MIN_BARS:
        return None
    for level in range(relax + 1):
        f = level_frame(df, level, params)
        last = f.iloc[-1]
        if last["loser"] != "":
            return {
                "candle_start": f.index[-1],
                "loser": last["loser"],
                "mirror": last["mirror"],
                "regime": last["regime"],
                "relax": level,
                "price": float(last["close"]),
                "atr": float(last["atr"]),
                "rsi": float(last["rsi"]),
                "er": float(last["er"]),
                "vwap": float(last["vwap"]),
            }
    return None
