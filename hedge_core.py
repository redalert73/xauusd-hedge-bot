# ==========================================
# NUCLEO COMUNE LIVE + BACKTEST
# ==========================================
# Livelli, orari ed esito dei trade vivono qui, cosi' il bot live e il
# backtest usano esattamente le stesse regole.

import pandas as pd

import config

CANDLE_MIN = 5


# ---------- tempo ----------
def to_rome(ts_utc_naive):
    """Timestamp UTC (naive, come li restituisce Twelve Data con timezone=UTC) -> ora italiana."""
    return pd.Timestamp(ts_utc_naive).tz_localize("UTC").tz_convert(config.TIMEZONE)


def candle_end_rome(candle_start_utc_naive):
    return to_rome(candle_start_utc_naive) + pd.Timedelta(minutes=CANDLE_MIN)


def in_signal_window(dt_rome):
    t = dt_rome.time()
    return config.SIGNAL_START <= t < config.SIGNAL_END


def at_or_past_force_close(dt_rome):
    return dt_rome.time() >= config.FORCE_CLOSE


# ---------- direzioni e livelli ----------
def opposite(direction):
    return "SELL" if direction == "BUY" else "BUY"


def levels(entry, loser_dir):
    """Livelli di prezzo per la gamba PERDENTE e per quella SPECULARE."""
    sgn = 1 if loser_dir == "BUY" else -1
    loser = {
        "dir": loser_dir,
        "entry": entry,
        "sl": entry - sgn * config.SL_POINTS,        # obiettivo
        "tp": entry + sgn * config.TP_POINTS,        # da evitare
        "slip": entry - sgn * config.SLIPPAGE_POINTS,  # limite da non raggiungere
    }
    mirror = {
        "dir": opposite(loser_dir),
        "entry": entry,
        "tp": loser["sl"],   # il TP dello speculare coincide con lo SL del perdente
        "sl": loser["tp"],   # lo SL dello speculare coincide con il TP del perdente
    }
    return loser, mirror


# ---------- esito di una candela ----------
def step_outcome(loser_dir, entry, high, low):
    """Valuta una candela CHIUSA per la gamba perdente.

    Ritorna (esito, slip_breach, adverse_usd) con esito in
    None | "SL" | "TP" | "AMBIGUO" (SL e TP toccati nella stessa candela:
    l'ordine reale non e' ricostruibile da dati M5).
    slip_breach = True se la candela ha percorso oltre il limite slippage.
    """
    if loser_dir == "BUY":
        adverse = entry - low
        favorable = high - entry
    else:
        adverse = high - entry
        favorable = entry - low
    adverse = max(adverse, 0.0)
    hit_sl = adverse >= config.SL_POINTS
    hit_tp = favorable >= config.TP_POINTS
    slip = adverse >= config.SLIPPAGE_POINTS
    adverse_usd = adverse * config.USD_PER_POINT
    if hit_sl and hit_tp:
        return "AMBIGUO", slip, adverse_usd
    if hit_sl:
        return "SL", slip, adverse_usd
    if hit_tp:
        return "TP", slip, adverse_usd
    return None, slip, adverse_usd


def pnl_usd(loser_dir, entry, exit_price):
    sgn = 1 if loser_dir == "BUY" else -1
    return (exit_price - entry) * sgn * config.USD_PER_POINT


# ---------- formattazione ----------
def fmt_usd(x, sign=False):
    s = f"{abs(x):,.0f}".replace(",", ".")
    if sign:
        return f"{'+' if x >= 0 else '-'}{s}$"
    return f"{s}$"
