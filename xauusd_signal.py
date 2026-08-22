from datetime import datetime
import json
import os
from zoneinfo import ZoneInfo
import pandas as pd
import requests

STATE_FILE = "state/xauusd_state.json"
LOT_SIZE = 1.04

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
NTFY_TOPIC = os.getenv(
    "NTFY_TOPIC", "xauusd_signal_77ax"
)  # Fallback sul tuo topic


def get_current_rome_time():
    rome_tz = ZoneInfo("Europe/Rome")
    return datetime.now(rome_tz)


def is_within_trading_hours():
    now_rome = get_current_rome_time()
    return 6 <= now_rome.hour < 20


def fetch_ohlcv_data():
    if not TWELVE_DATA_API_KEY:
        print("ERRORE: Manca la chiave API nei Secrets.")
        return None

    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=100&apikey={TWELVE_DATA_API_KEY}"

    try:
        response = requests.get(url, timeout=15)
        data = response.json()

        if "values" in data:
            df = pd.DataFrame(data["values"])
            df = df.iloc[::-1].reset_index(drop=True)

            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col])

            df["volume"] = (
                pd.to_numeric(df["volume"]) if "volume" in df.columns else 1.0
            )
            return df
    except Exception as e:
        print(f"Errore connessione: {e}")
    return None


def calculate_indicators(df):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()
    return df


def get_structural_liquidity(df, window=3):
    storico = df.iloc[:-1]
    swing_lows = []
    swing_highs = []

    for i in range(window, len(storico) - window):
        current_low = storico["low"].iloc[i]
        current_high = storico["high"].iloc[i]

        if all(
            current_low <= storico["low"].iloc[i - j]
            for j in range(1, window + 1)
        ) and all(
            current_low <= storico["low"].iloc[i + j]
            for j in range(1, window + 1)
        ):
            swing_lows.append(current_low)

        if all(
            current_high >= storico["high"].iloc[i - j]
            for j in range(1, window + 1)
        ) and all(
            current_high >= storico["high"].iloc[i + j]
            for j in range(1, window + 1)
        ):
            swing_highs.append(current_high)

    major_liquidity_low = (
        min(swing_lows) if swing_lows else storico["low"].min()
    )
    major_liquidity_high = (
        max(swing_highs) if swing_highs else storico["high"].max()
    )

    return major_liquidity_low, major_liquidity_high


def load_state():
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {
        "last_signal_price": None,
        "last_signal_direction": None,
        "last_signal_date": None,
    }


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


def send_notifications(message_md):
    # 1. Invio su Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url_tg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload_tg = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message_md,
            "parse_mode": "Markdown",
        }
        try:
            requests.post(url_tg, json=payload_tg, timeout=10)
        except Exception as e:
            print(f"Errore invio Telegram: {e}")

    # 2. Invio su ntfy.sh (Bypassa qualsiasi blocco di notifica Android)
    if NTFY_TOPIC:
        url_ntfy = f"https://ntfy.sh/{NTFY_TOPIC}"
        try:
            requests.post(
                url_ntfy,
                data=message_md.encode("utf-8"),
                headers={
                    "Title": "🚨 Segnale XAU/USD Attivato",
                    "Tags": "moneybag,chart_with_upwards_trend",
                    "Priority": "urgent",
                },
                timeout=10,
            )
        except Exception as e:
            print(f"Errore invio ntfy: {e}")


def main():
    if not is_within_trading_hours():
        print("Fuori fascia oraria.")
        return

    now_rome = get_current_rome_time()
    today_str = now_rome.strftime("%Y-%m-%d")

    state = load_state()
    if state.get("last_signal_date") == today_str:
        print("⚠️ Un segnale è già stato eseguito oggi. Stop operativo.")
        return

    df = fetch_ohlcv_data()
    if df is None or df.empty or len(df) < 50:
        print("Dati insufficienti.")
        return

    df = calculate_indicators(df)
    liq_low, liq_high = get_structural_liquidity(df, window=3)

    current_price = df["close"].iloc[-1]
    current_low = df["low"].iloc[-1]
    current_high = df["high"].iloc[-1]
    current_atr = df["atr"].iloc[-1]

    if pd.isna(current_atr) or current_atr < 0.25:
        return

    signal_direction = None
    sl_distance = max(round(current_atr * 2.0, 2), 18.0)
    tp_distance = max(round(current_atr * 2.5, 2), 22.0)

    if current_low < liq_low:
        signal_direction = "BUY"
        sl_price = round(current_price - sl_distance, 2)
        tp_price = round(current_price + tp_distance, 2)
    elif current_high > liq_high:
        signal_direction = "SELL"
        sl_price = round(current_price + sl_distance, 2)
        tp_price = round(current_price - tp_distance, 2)
    else:
        return

    state["last_signal_price"] = current_price
    state["last_signal_direction"] = signal_direction
    state["last_signal_date"] = today_str
    save_state(state)

    emoji = "🟢" if signal_direction == "BUY" else "🔴"
    message = (
        f"{emoji} SEGNALE XAU/USD (DAILY UNICO) {emoji}\n\n"
        f"• Ordine: {signal_direction}\n"
        f"• Lotti: {LOT_SIZE}\n"
        f"• Prezzo: {current_price}\n\n"
        f"🎯 Take Profit: {tp_price}\n"
        f"🛑 Stop Loss: {sl_price}"
    )

    send_notifications(message)


if __name__ == "__main__":
    main()
