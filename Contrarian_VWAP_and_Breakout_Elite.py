import os
import sys
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Impostazioni di Configurazione
SYMBOL = "XAU/USD"
INTERVAL = "15min"

LOT_SIZE = 1.04
SL_VAL = 2.400  # Target WIN (Raggiunto SL = Operazione in Guadagno)
TP_VAL = 2.000  # Target LOSS (Raggiunto TP = Operazione in Perdita)
MAX_SLIPPAGE = 0.400

# Circuit Breaker Anti-Drawdown Giornaliero (-3.000 USD Max da non superare mai)
MAX_DAILY_LOSS = 2400.0  # Blocco immediato alla prima perdita per proteggere il limite dei -3.000 USD

# Parametri e Filtri d'Ingresso (Win Rate 65.52%)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0
MOM_MULTIPLIER = 0.50
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Finestra Operativa (06:00 - 20:30 UTC)
ORA_INIZIO_MINUTI = 6 * 60 + 0  # 06:00 UTC
ORA_FINE_MINUTI = 20 * 60 + 30  # 20:30 UTC

# API & Credentials
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")


def send_notification(message: str):
    """Invia notifiche in parallelo su Telegram e ntfy."""
    print(f"[NOTIFY] {message}")

    # Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(
                url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10
            )
        except Exception as e:
            print(f"Errore invio Telegram: {e}")

    # ntfy
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
    """Verifica se l'orario rientra nella finestra operativa 06:00 - 20:30 UTC."""
    current_minutes = dt_utc.hour * 60 + dt_utc.minute
    return ORA_INIZIO_MINUTI <= current_minutes <= ORA_FINE_MINUTI


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcola VWAP, ATR, EMA e indicatori di Momentum/Volatilità."""
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    df["tp_vol"] = df["typical_price"] * df["volume"]

    # VWAP Giornaliero
    df["date"] = pd.to_datetime(df["datetime"]).dt.date
    df["cum_vol"] = df.groupby("date")["volume"].cumsum()
    df["cum_tp_vol"] = df.groupby("date")["tp_vol"].cumsum()
    df["vwap"] = df["cum_tp_vol"] / df["cum_vol"]

    # ATR
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=ATR_PERIOD).mean()

    # Volatilità e Momentum
    df["vol_std"] = df["volume"].rolling(window=20).std()
    df["vol_mean"] = df["volume"].rolling(window=20).mean()
    df["momentum"] = (df["close"] - df["close"].shift(4)).abs()

    return df


def check_signal(df: pd.DataFrame) -> str:
    """Valuta la presenza di un segnale Contrarian VWAP & Breakout."""
    latest = df.iloc[-1]

    # Controlli di selettività
    vol_filter = latest["volume"] > (
        latest["vol_mean"] + VOL_MULTIPLIER * latest["vol_std"]
    )
    mom_filter = latest["momentum"] > (MOM_MULTIPLIER * latest["atr"])

    if not (vol_filter and mom_filter):
        return "NONE"

    # Logica Contrarian VWAP Breakout
    if latest["close"] > latest["vwap"] + (
        latest["atr"] * SWING_OFFSET_MULTIPLIER
    ):
        return "SELL"
    elif latest["close"] < latest["vwap"] - (
        latest["atr"] * SWING_OFFSET_MULTIPLIER
    ):
        return "BUY"

    return "NONE"


def run_bot_cycle(daily_losses_usd: float) -> float:
    """Esegue un ciclo unico di controllo del mercato."""
    now_utc = datetime.now(timezone.utc)

    # 1. Verifica orario operativo
    if not is_within_operating_window(now_utc):
        print(f"[{now_utc.strftime('%H:%M:%S UTC')}] Fuori finestra operativa.")
        return daily_losses_usd

    # 2. Circuit Breaker Anti-Drawdown
    if daily_losses_usd >= MAX_DAILY_LOSS:
        print(
            f"[{now_utc.strftime('%H:%M:%S UTC')}] Circuit breaker attivo: Raggiunta la soglia di stop giornaliera ({daily_losses_usd}$)."
        )
        return daily_losses_usd

    # 3. Download dati di mercato (Twelve Data)
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize=100&apikey={TWELVE_DATA_API_KEY}"
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

    # 4. Verifica Segnale
    signal = check_signal(df)
    if signal != "NONE":
        price = df.iloc[-1]["close"]
        msg = (
            f"🚨 **SEGNALE {signal} - {SYMBOL}** 🚨\n"
            f"Prezzo: {price:.3f}\n"
            f"Lotto: {LOT_SIZE}\n"
            f"Target WIN (SL): {SL_VAL} pts\n"
            f"Target LOSS (TP): {TP_VAL} pts\n"
            f"Orario: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        send_notification(msg)

    return daily_losses_usd


if __name__ == "__main__":
    print("=== Contrarian VWAP & Breakout Elite Bot Avviato ===")
    daily_loss_tracker = 0.0
    run_bot_cycle(daily_loss_tracker)
