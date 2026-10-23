import os
import sys
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import config

# API & Credentials (Environment Variables)
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")


def send_notification(message: str):
    """Invia notifiche in parallelo su Telegram e ntfy."""
    print(f"[NOTIFY] {message}")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(
                url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10
            )
        except Exception as e:
            print(f"Errore invio Telegram: {e}")

    if NTFY_TOPIC:
        try:
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=message.encode("utf-8"),
                timeout=10,
            )
        except Exception as e:
            print(f"Errore invio ntfy: {e}")


def is_within_operating_window(dt_utc: datetime) -> bool:
    """Verifica se l'orario rientra nella finestra operativa."""
    current_minutes = dt_utc.hour * 60 + dt_utc.minute
    return config.ORA_INIZIO_MINUTI <= current_minutes <= config.ORA_FINE_MINUTI


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcola VWAP, ATR e indicatori di Momentum/Volatilità."""
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    df["tp_vol"] = df["typical_price"] * df["volume"]

    df["date"] = pd.to_datetime(df["datetime"]).dt.date
    df["cum_vol"] = df.groupby("date")["volume"].cumsum()
    df["cum_tp_vol"] = df.groupby("date")["tp_vol"].cumsum()
    df["vwap"] = df["cum_tp_vol"] / df["cum_vol"]

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=config.ATR_PERIOD).mean()

    df["vol_std"] = df["volume"].rolling(window=20).std()
    df["vol_mean"] = df["volume"].rolling(window=20).mean()
    df["momentum"] = (df["close"] - df["close"].shift(4)).abs()

    return df


def check_signal(df: pd.DataFrame) -> str:
    """Valuta la presenza di un segnale Contrarian VWAP & Breakout."""
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    vol_filter = latest["volume"] > (
        latest["vol_mean"] + config.VOL_MULTIPLIER * latest["vol_std"]
    )
    mom_filter = latest["momentum"] > (config.MOM_MULTIPLIER * latest["atr"])
    micro_trend_ok = abs(latest["close"] - prev["close"]) > (0.1 * latest["atr"])

    if not (vol_filter and mom_filter and micro_trend_ok):
        return "NONE"

    if latest["close"] > latest["vwap"] + (
        latest["atr"] * config.SWING_OFFSET_MULTIPLIER
    ):
        return "SELL"
    elif latest["close"] < latest["vwap"] - (
        latest["atr"] * config.SWING_OFFSET_MULTIPLIER
    ):
        return "BUY"

    return "NONE"


def run_bot_cycle(daily_losses_usd: float) -> float:
    """Esegue un ciclo unico di controllo del mercato."""
    now_utc = datetime.now(timezone.utc)

    if not is_within_operating_window(now_utc):
        print(f"[{now_utc.strftime('%H:%M:%S UTC')}] Fuori finestra operativa.")
        return daily_losses_usd

    if daily_losses_usd >= config.MAX_DAILY_LOSS:
        print(
            f"[{now_utc.strftime('%H:%M:%S UTC')}] Circuit breaker attivo ({daily_losses_usd}$)."
        )
        return daily_losses_usd

    url = f"https://api.twelvedata.com/time_series?symbol={config.SYMBOL}&interval={config.INTERVAL}&outputsize=100&apikey={TWELVE_DATA_API_KEY}"
    res = requests.get(url).json()

    if "values" not in res:
        print("Errore nel recupero dati API Twelve Data.")
        return daily_losses_usd

    df = pd.DataFrame(res["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df.sort_values("datetime").reset_index(drop=True)
    df = calculate_indicators(df)

    signal = check_signal(df)
    if signal != "NONE":
        price = df.iloc[-1]["close"]
        msg = (
            f"🚨 **SEGNALE {signal} - {config.SYMBOL}** 🚨\n"
            f"Prezzo: {price:.3f}\n"
            f"Lotto: {config.LOT_SIZE}\n"
            f"Target WIN (SL): {config.SL_VAL} pts\n"
            f"Target LOSS (TP): {config.TP_VAL} pts\n"
            f"Orario: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        send_notification(msg)

    return daily_losses_usd


if __name__ == "__main__":
    print("=== Contrarian VWAP & Breakout Elite Bot Avviato (Config Centralizzata) ===")
    daily_loss_tracker = 0.0
    run_bot_cycle(daily_loss_tracker)
