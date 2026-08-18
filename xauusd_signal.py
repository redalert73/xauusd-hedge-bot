from datetime import datetime
import json
import os
from zoneinfo import ZoneInfo
import pandas as pd
import requests

# Parametri e Costanti
STATE_FILE = "state/xauusd_state.json"
SL_DISTANCE = 25.96  # Produce lo Stop Loss di -$2.700 USD su 1.04 lotti
TP_DISTANCE = 28.85  # Produce il Take Profit di +$3.000 USD su 1.04 lotti
LOT_SIZE = 1.04
MIN_ATR_THRESHOLD = 1.20  # Soglia minima di volatilità (in $ sulla candela a 15m)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")


def is_within_trading_hours():
    """Verifica se l'ora attuale rientra nella finestra consentita (06:00 - 18:00 ora italiana)."""
    rome_tz = ZoneInfo("Europe/Rome")
    now_rome = datetime.now(rome_tz)
    start_hour = 6
    end_hour = 18

    is_valid = start_hour <= now_rome.hour < end_hour
    print(
        f"Ora locale (Italia): {now_rome.strftime('%H:%M:%S')} | Operatività attiva: {'SI' if is_valid else 'NO'}"
    )
    return is_valid


def fetch_ohlcv_data():
    """Recupera le ultime 100 candele a 15 minuti da Twelve Data per l'analisi."""
    if not TWELVE_DATA_API_KEY:
        print("ERRORE: Manca la chiave TWELVE_DATA_API_KEY nei Secrets.")
        return None

    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=15min&outputsize=100&apikey={TWELVE_DATA_API_KEY}"

    try:
        response = requests.get(url, timeout=15)
        data = response.json()

        if "values" in data:
            df = pd.DataFrame(data["values"])

            # Invertiamo l'ordine per avere il passato in alto e il presente in basso
            df = df.iloc[::-1].reset_index(drop=True)

            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col])

            if "volume" in df.columns:
                df["volume"] = pd.to_numeric(df["volume"])
            else:
                df["volume"] = 1.0

            return df
        else:
            print(f"Errore API Twelve Data: {data}")
            return None
    except Exception as e:
        print(f"Errore connessione API: {e}")
        return None


def calculate_atr(df, period=14):
    """Calcola l'Average True Range (ATR) per misurare la volatilità del mercato."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return round(atr.iloc[-1], 2)


def calculate_poc(df):
    """Calcola il Point of Control (POC) dal Volume Profile."""
    volume_profile = {}

    for index, row in df.iterrows():
        typical_price = round((row["high"] + row["low"] + row["close"]) / 3, 1)
        vol = row["volume"]
        volume_profile[typical_price] = (
            volume_profile.get(typical_price, 0) + vol
        )

    poc_price = max(volume_profile, key=volume_profile.get)
    return poc_price


def get_structural_liquidity(df, window=4):
    """Individua i punti di swing per definire la Liquidità Strutturale."""
    swing_lows = []
    swing_highs = []

    storico = df.iloc[:-1]

    for i in range(window, len(storico) - window):
        current_low = storico["low"].iloc[i]
        current_high = storico["high"].iloc[i]

        is_low = all(
            current_low <= storico["low"].iloc[i - j]
            for j in range(1, window + 1)
        ) and all(
            current_low <= storico["low"].iloc[i + j]
            for j in range(1, window + 1)
        )

        is_high = all(
            current_high >= storico["high"].iloc[i - j]
            for j in range(1, window + 1)
        ) and all(
            current_high >= storico["high"].iloc[i + j]
            for j in range(1, window + 1)
        )

        if is_low:
            swing_lows.append(current_low)
        if is_high:
            swing_highs.append(current_high)

    major_liquidity_low = min(swing_lows) if swing_lows else storico["low"].min()
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
    return {"last_signal_price": None, "last_signal_direction": None}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERRORE: Credentials Telegram mancanti.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    requests.post(url, json=payload, timeout=10)


def main():
    # 1. Filtro Orario (Operatività 06:00 - 18:00 Italia)
    if not is_within_trading_hours():
        print(
            "Fuori dalla finestra di trading autorizzata (06:00 - 18:00). Standby."
        )
        return

    # 2. Recupero Dati
    df = fetch_ohlcv_data()
    if df is None or df.empty:
        print("Impossibile scaricare le candele.")
        return

    # Calcolo Volatilità (ATR 14) e Volume SMA 20
    current_atr = calculate_atr(df)
    df["vol_sma_20"] = df["volume"].rolling(window=20).mean()

    current_price = df["close"].iloc[-1]
    current_volume = df["volume"].iloc[-1]
    avg_volume = df["vol_sma_20"].iloc[-1]

    poc_price = calculate_poc(df)
    liq_low, liq_high = get_structural_liquidity(df)

    is_high_volume = current_volume > avg_volume
    is_volatile_enough = current_atr >= MIN_ATR_THRESHOLD

    print(f"Prezzo Attuale: {current_price}")
    print(
        f"ATR (Volatilità): {current_atr} (Minimo richiesto: {MIN_ATR_THRESHOLD})"
    )
    print(
        f"Spike Volumi: {'SI' if is_high_volume else 'NO'} | Volatilità idonea: {'SI' if is_volatile_enough else 'NO'}"
    )

    # 3. Logica Anti-Trend Avanzata con tutti i filtri attivi
    signal_direction = None
    sl_price = 0.0
    tp_price = 0.0

    if (
        current_price < liq_low
        and current_price < poc_price
        and is_high_volume
        and is_volatile_enough
    ):
        signal_direction = "BUY"
        sl_price = round(current_price - SL_DISTANCE, 2)
        tp_price = round(current_price + TP_DISTANCE, 2)

    elif (
        current_price > liq_high
        and current_price > poc_price
        and is_high_volume
        and is_volatile_enough
    ):
        signal_direction = "SELL"
        sl_price = round(current_price + SL_DISTANCE, 2)
        tp_price = round(current_price - TP_DISTANCE, 2)

    else:
        print(
            "Condizioni incomplete (Sweep, POC, Volumi o ATR non conformi). Standby."
        )
        return

    # 4. Controllo Duplicati
    state = load_state()
    if (
        state.get("last_signal_price") == current_price
        and state.get("last_signal_direction") == signal_direction
    ):
        print("Segnale già notificato.")
        return

    state["last_signal_price"] = current_price
    state["last_signal_direction"] = signal_direction
    save_state(state)

    # 5. Notifica Telegram
    emoji = "🟢" if signal_direction == "BUY" else "🔴"
    message = (
        f"{emoji} *SEGNALE STRUTTURALE OTTIMIZZATO XAU/USD* {emoji}\n\n"
        f"• *Ordine:* `{signal_direction}`\n"
        f"• *Lotti:* `{LOT_SIZE}`\n"
        f"• *Prezzo Attuale:* `{current_price}`\n\n"
        f"📊 *Conferme Tecniche:*\n"
        f"• *Sweep Liquidity:* Rottura livello `{liq_low if signal_direction == 'BUY' else liq_high}`\n"
        f"• *POC:* `{poc_price}` (Schiaccia il prezzo)\n"
        f"• *Volatilità (ATR 14):* `{current_atr}` (OK)\n"
        f"• *Volume Spike:* `SI`\n\n"
        f"🎯 *Take Profit (+3000 USD):* `{tp_price}`\n"
        f"🛑 *Stop Loss (-2700 USD):* `{sl_price}`\n\n"
        f"⚠️ *Nota Operativa:* Rispetta sempre i **${SL_DISTANCE}** di distanza dallo SL dal prezzo a cui entri a mercato!"
    )
    send_telegram_message(message)


if __name__ == "__main__":
    main()
