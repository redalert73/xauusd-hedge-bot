from datetime import datetime
import json
import os
from zoneinfo import ZoneInfo
import pandas as pd
import requests

# Parametri e Costanti
STATE_FILE = "state/xauusd_state.json"
LOT_SIZE = 1.04
MIN_ATR_THRESHOLD = 0.35  # Soglia minima di volatilità ottimizzata

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")


def is_within_trading_hours():
    """Verifica operatività (06:00 - 20:00 ora italiana)."""
    rome_tz = ZoneInfo("Europe/Rome")
    now_rome = datetime.now(rome_tz)
    return 6 <= now_rome.hour < 20


def fetch_ohlcv_data():
    """Recupera le ultime 100 candele a 5 minuti da Twelve Data."""
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
        else:
            print(f"Errore API: {data}")
            return None
    except Exception as e:
        print(f"Errore connessione: {e}")
        return None


def calculate_indicators(df):
    """Calcola ATR, POC, Medie Mobili (EMA 50 e EMA 200) per il massimo filtraggio."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()

    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["vol_sma_20"] = df["volume"].rolling(window=20).mean()

    volume_profile = {}
    for index, row in df.iterrows():
        typical_price = round(
            (row["high"] + row["low"] + row["close"]) / 3, 1
        )
        volume_profile[typical_price] = (
            volume_profile.get(typical_price, 0) + row["volume"]
        )
    poc_price = max(volume_profile, key=volume_profile.get)

    return df, poc_price


def get_structural_liquidity(df, window=5):
    """Indole zone di liquidità strutturale (Swing Highs e Lows estesi)."""
    swing_lows, swing_highs = [], []
    storico = df.iloc[:-1]

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
    return {"last_signal_price": None, "last_signal_direction": None, "signal_count": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    requests.post(url, json=payload, timeout=10)


def main():
    if not is_within_trading_hours():
        print("Fuori fascia oraria 06:00 - 20:00.")
        return

    df = fetch_ohlcv_data()
    if df is None or df.empty or len(df) < 200:
        print("Dati insufficienti per il calcolo avanzato.")
        return

    df, poc_price = calculate_indicators(df)
    liq_low, liq_high = get_structural_liquidity(df)

    current_price = df["close"].iloc[-1]
    current_open = df["open"].iloc[-1]
    current_low = df["low"].iloc[-1]
    current_high = df["high"].iloc[-1]
    current_atr = df["atr"].iloc[-1]
    current_ema50 = df["ema_50"].iloc[-1]
    current_ema200 = df["ema_200"].iloc[-1]

    is_volatile = current_atr >= MIN_ATR_THRESHOLD
    
    # Conferma di reiezione tramite Price Action (Wick / Ombra pronunciata)
    lower_wick = min(current_open, current_price) - current_low
    upper_wick = current_high - max(current_open, current_price)
    body_size = abs(current_close_diff := current_price - current_open)

    print(f"Prezzo: {current_price} | POC: {poc_price} | ATR: {round(current_atr, 2)}")
    print(f"Liq Low: {liq_low} | Liq High: {liq_high}")

    signal_direction = None

    # Calcolo dinamico di SL e TP istituzionale (Rischio/Rendimento 1:1.3 con ATR)
    sl_distance = max(round(current_atr * 2.2, 2), 22.0)
    tp_distance = max(round(current_atr * 3.0, 2), 30.0)

    # Condizione BUY Master: Sweep della liquidità inferiore + reiezione dal basso + trend ribassista di breve che si inverte
    if (current_low < liq_low and current_price < poc_price and is_volatile and 
        current_price < current_ema50 and lower_wick > (body_size * 0.8)):
        signal_direction = "BUY"
        sl_price = round(current_price - sl_distance, 2)
        tp_price = round(current_price + tp_distance, 2)

    # Condizione SELL Master: Sweep della liquidità superiore + reiezione dall'alto + trend rialzista di breve che si inverte
    elif (current_high > liq_high and current_price > poc_price and is_volatile and 
          current_price > current_ema50 and upper_wick > (body_size * 0.8)):
        signal_direction = "SELL"
        sl_price = round(current_price + sl_distance, 2)
        tp_price = round(current_price - tp_distance, 2)
    else:
        print("Condizioni Master Anti-Trend non pienamente soddisfatte. Standby.")
        return

    state = load_state()
    # Controllo per evitare segnali identici consecutivi
    if (state.get("last_signal_price") == current_price and 
        state.get("last_signal_direction") == signal_direction):
        return

    state["last_signal_price"] = current_price
    state["last_signal_direction"] = signal_direction
    state["signal_count"] = state.get("signal_count", 0) + 1
    save_state(state)

    emoji = "🟢" if signal_direction == "BUY" else "🔴"
    message = (
        f"{emoji} *SEGNALE MASTER INSTITUTIONAL* {emoji}\n\n"
        f"• *Ordine:* `{signal_direction}`\n"
        f"• *Lotti:* `{LOT_SIZE}`\n"
        f"• *Prezzo Attuale:* `{current_price}`\n\n"
        f"💎 *Filtri di Precisione Avanzati:*\n"
        f"• *Sweep & Rejection:* Rilevata ombra di reiezione sul livello\n"
        f"• *POC Volume Point:* `{poc_price}`\n"
        f"• *Volatilità ATR:* `{round(current_atr, 2)}`\n\n"
        f"🎯 *Take Profit (Master):* `{tp_price}`\n"
        f"🛑 *Stop Loss (Master):* `{sl_price}`\n\n"
        f"⚡ *Profilo di Rischio:* Gestione dinamica a favore di reiezione strutturale."
    )
    send_telegram_message(message)


if __name__ == "__main__":
    main()
