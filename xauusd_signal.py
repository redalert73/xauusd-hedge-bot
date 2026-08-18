from datetime import datetime
import json
import os
from zoneinfo import ZoneInfo
import pandas as pd
import requests

# Parametri e Costanti
STATE_FILE = "state/xauusd_state.json"
SL_DISTANCE = 25.96  # Stop Loss di -$2.700 USD su 1.04 lotti
TP_DISTANCE = 28.85  # Take Profit di +$3.000 USD su 1.04 lotti
LOT_SIZE = 1.04
MIN_ATR_THRESHOLD = 0.60  # Soglia minima volatilità su candela a 5m

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")


def is_within_trading_hours():
    """Verifica operatività (06:00 - 18:00 ora italiana)."""
    rome_tz = ZoneInfo("Europe/Rome")
    now_rome = datetime.now(rome_tz)
    return 6 <= now_rome.hour < 18


def fetch_ohlcv_data():
    """Recupera le ultime 100 candele a 5 minuti da Twelve Data."""
    if not TWELVE_DATA_API_KEY:
        print("ERRORE: Manca la chiave API nei Secrets.")
        return None

    # Cambiato a 5min per allineamento perfetto con il Cron di GitHub
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=100&apikey={TWELVE_DATA_API_KEY}"

    try:
        response = requests.get(url, timeout=15)
        data = response.json()

        if "values" in data:
            df = pd.DataFrame(data["values"])
            df = df.iloc[::-1].reset_index(drop=True)

            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col])

            df["volume"] = pd.to_numeric(df["volume"]) if "volume" in df.columns else 1.0
            return df
        else:
            print(f"Errore API: {data}")
            return None
    except Exception as e:
        print(f"Errore connessione: {e}")
        return None


def calculate_indicators(df):
    """Calcola ATR, POC, SMA Volumi e la EMA 50 per il trend di fondo."""
    # ATR 14
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()

    # EMA 50 (Filtro Trend di Fondo)
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    
    # Volume SMA 20
    df["vol_sma_20"] = df["volume"].rolling(window=20).mean()

    # POC
    volume_profile = {}
    for index, row in df.iterrows():
        typical_price = round((row["high"] + row["low"] + row["close"]) / 3, 1)
        volume_profile[typical_price] = volume_profile.get(typical_price, 0) + row["volume"]
    poc_price = max(volume_profile, key=volume_profile.get)

    return df, poc_price


def get_structural_liquidity(df, window=4):
    """Trova le zone di liquidità (Swing Highs e Lows)."""
    swing_lows, swing_highs = [], []
    storico = df.iloc[:-1]

    for i in range(window, len(storico) - window):
        current_low = storico["low"].iloc[i]
        current_high = storico["high"].iloc[i]

        if all(current_low <= storico["low"].iloc[i - j] for j in range(1, window + 1)) and \
           all(current_low <= storico["low"].iloc[i + j] for j in range(1, window + 1)):
            swing_lows.append(current_low)
            
        if all(current_high >= storico["high"].iloc[i - j] for j in range(1, window + 1)) and \
           all(current_high >= storico["high"].iloc[i + j] for j in range(1, window + 1)):
            swing_highs.append(current_high)

    major_liquidity_low = min(swing_lows) if swing_lows else storico["low"].min()
    major_liquidity_high = max(swing_highs) if swing_highs else storico["high"].max()

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
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=10)


def main():
    if not is_within_trading_hours():
        print("Fuori fascia oraria 06:00 - 18:00.")
        return

    df = fetch_ohlcv_data()
    if df is None or df.empty:
        return

    df, poc_price = calculate_indicators(df)
    liq_low, liq_high = get_structural_liquidity(df)

    # Dati ultima candela
    current_price = df["close"].iloc[-1]
    current_open = df["open"].iloc[-1]
    current_volume = df["volume"].iloc[-1]
    avg_volume = df["vol_sma_20"].iloc[-1]
    current_atr = df["atr"].iloc[-1]
    current_ema = df["ema_50"].iloc[-1]

    # Condizioni
    is_high_volume = current_volume > avg_volume
    is_volatile = current_atr >= MIN_ATR_THRESHOLD
    
    # Conferma direzionale: per fare danni al tuo conto, la candela deve spingere forte e il trend deve essere avverso
    is_red_candle = current_price < current_open
    is_green_candle = current_price > current_open
    bearish_trend = current_price < current_ema
    bullish_trend = current_price > current_ema

    print(f"Prezzo: {current_price} | POC: {poc_price} | EMA50: {round(current_ema, 2)}")
    print(f"Liq Low: {liq_low} | Liq High: {liq_high}")

    signal_direction = None

    # BUY ASSASSINO: Mercato crolla (Sotto Liq Low, POC spinge giù, Trend ribassista, Candela rossa, Volumi e ATR alti)
    if (current_price < liq_low and current_price < poc_price and 
        is_high_volume and is_volatile and bearish_trend and is_red_candle):
        signal_direction = "BUY"
        sl_price = round(current_price - SL_DISTANCE, 2)
        tp_price = round(current_price + TP_DISTANCE, 2)

    # SELL ASSASSINO: Mercato esplode (Sopra Liq High, POC spinge su, Trend rialzista, Candela verde, Volumi e ATR alti)
    elif (current_price > liq_high and current_price > poc_price and 
          is_high_volume and is_volatile and bullish_trend and is_green_candle):
        signal_direction = "SELL"
        sl_price = round(current_price + SL_DISTANCE, 2)
        tp_price = round(current_price - TP_DISTANCE, 2)
    else:
        print("Condizioni di coerenza Anti-Trend non pienamente soddisfatte. Standby.")
        return

    state = load_state()
    if state.get("last_signal_price") == current_price and state.get("last_signal_direction") == signal_direction:
        return

    state["last_signal_price"] = current_price
    state["last_signal_direction"] = signal_direction
    save_state(state)

    emoji = "🟢" if signal_direction == "BUY" else "🔴"
    message = (
        f"{emoji} *SEGNALE ANTI-TREND COERENTE* {emoji}\n\n"
        f"• *Ordine:* `{signal_direction}`\n"
        f"• *Lotti:* `{LOT_SIZE}`\n"
        f"• *Prezzo Attuale:* `{current_price}`\n\n"
        f"📊 *Filtri Anti-Inversione (OK):*\n"
        f"• *Sweep Liquidity:* Rottura `{liq_low if signal_direction == 'BUY' else liq_high}`\n"
        f"• *POC:* `{poc_price}` (Schiaccia il prezzo)\n"
        f"• *Trend Base (EMA 50):* `{round(current_ema, 2)}` (A favore del Breakout)\n"
        f"• *Volume & Volatilità:* Elevati\n\n"
        f"🎯 *Take Profit (+3000 USD):* `{tp_price}`\n"
        f"🛑 *Stop Loss (-2700 USD):* `{sl_price}`\n\n"
        f"⚠️ *Nota Operativa:* Rispetta sempre i **${SL_DISTANCE}** di distanza dallo SL dal prezzo a cui entri a mercato!"
    )
    send_telegram_message(message)

if __name__ == "__main__":
    main()
