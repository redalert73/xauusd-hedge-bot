import json
import os
import requests
import pandas as pd

# Parametri e Costanti
STATE_FILE = "state/xauusd_state.json"
SL_DISTANCE = 25.96  # Produce lo Stop Loss di -$2.700 USD su 1.04 lotti
TP_DISTANCE = 28.85  # Produce il Take Profit di +$3.000 USD su 1.04 lotti
LOT_SIZE = 1.04

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")


def fetch_ohlcv_data():
    """Recupera le ultime 100 candele a 15 minuti da Twelve Data per calcolare Liquidity e POC."""
    if not TWELVE_DATA_API_KEY:
        print("ERRORE: Manca la chiave TWELVE_DATA_API_KEY nei Secrets.")
        return None

    # Utilizziamo l'endpoint time_series per ottenere Open, High, Low, Close, Volume
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=15min&outputsize=100&apikey={TWELVE_DATA_API_KEY}"

    try:
        response = requests.get(url, timeout=15)
        data = response.json()

        if "values" in data:
            df = pd.DataFrame(data["values"])
            
            # Twelve Data fornisce i dati in ordine decrescente (il più recente in cima). Li invertiamo.
            df = df.iloc[::-1].reset_index(drop=True)
            
            # Convertiamo le stringhe in valori numerici
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col])
            
            if 'volume' in df.columns:
                df['volume'] = pd.to_numeric(df['volume'])
            else:
                df['volume'] = 1.0  # Fallback se il volume tick non è disponibile
                
            return df
        else:
            print(f"Errore API Twelve Data: {data}")
            return None
    except Exception as e:
        print(f"Errore connessione API: {e}")
        return None


def calculate_poc(df):
    """Calcola il Point of Control (POC) basato sul Volume Profile."""
    volume_profile = {}
    
    for index, row in df.iterrows():
        # Utilizziamo il prezzo tipico approssimato per raggruppare i volumi
        typical_price = round((row['high'] + row['low'] + row['close']) / 3, 1)
        vol = row['volume']
        volume_profile[typical_price] = volume_profile.get(typical_price, 0) + vol
        
    # Il POC è il livello di prezzo con la somma di volumi maggiore
    poc_price = max(volume_profile, key=volume_profile.get)
    return poc_price


def get_structural_liquidity(df, window=4):
    """Individua i veri Swing Lows e Swing Highs per definire le zone di liquidità."""
    swing_lows = []
    swing_highs = []
    
    # Escludiamo l'ultima candela (in formazione)
    storico = df.iloc[:-1]
    
    for i in range(window, len(storico) - window):
        current_low = storico['low'].iloc[i]
        current_high = storico['high'].iloc[i]
        
        # È uno Swing Low se è il minimo assoluto rispetto alle N candele prima e dopo
        is_low = all(current_low <= storico['low'].iloc[i-j] for j in range(1, window+1)) and \
                 all(current_low <= storico['low'].iloc[i+j] for j in range(1, window+1))
                 
        # È uno Swing High se è il massimo assoluto rispetto alle N candele prima e dopo
        is_high = all(current_high >= storico['high'].iloc[i-j] for j in range(1, window+1)) and \
                  all(current_high >= storico['high'].iloc[i+j] for j in range(1, window+1))
                  
        if is_low:
            swing_lows.append(current_low)
        if is_high:
            swing_highs.append(current_high)
            
    # Prendiamo i livelli di liquidità più estremi registrati di recente
    major_liquidity_low = min(swing_lows) if swing_lows else storico['low'].min()
    major_liquidity_high = max(swing_highs) if swing_highs else storico['high'].max()
    
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
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=10)


def main():
    # 1. Recupero Dati Strutturali
    df = fetch_ohlcv_data()
    if df is None or df.empty:
        print("Impossibile scaricare le candele.")
        return

    current_price = df['close'].iloc[-1]
    poc_price = calculate_poc(df)
    liq_low, liq_high = get_structural_liquidity(df)

    print(f"Prezzo Attuale: {current_price}")
    print(f"POC (Point of Control): {poc_price}")
    print(f"Liquidità Inferiore (Sweep Low): {liq_low}")
    print(f"Liquidità Superiore (Sweep High): {liq_high}")

    signal_direction = None
    sl_price = 0.0
    tp_price = 0.0

    # 2. Logica Anti-Trend Avanzata (Liquidity Sweep + POC Check)
    # BUY: Rompe la liquidità inferiore (crollo) E il POC è sopra (schiaccia il prezzo verso lo SL)
    if current_price < liq_low and current_price < poc_price:
        signal_direction = "BUY"
        sl_price = round(current_price - SL_DISTANCE, 2)
        tp_price = round(current_price + TP_DISTANCE, 2)
        
    # SELL: Rompe la liquidità superiore (esplosione) E il POC è sotto (spinge il prezzo su verso lo SL)
    elif current_price > liq_high and current_price > poc_price:
        signal_direction = "SELL"
        sl_price = round(current_price + SL_DISTANCE, 2)
        tp_price = round(current_price - TP_DISTANCE, 2)
        
    else:
        print("Nessuno sweep di liquidità in corso o discordanza con il POC. Standby.")
        return

    # 3. Controllo Duplicati
    state = load_state()
    if state.get("last_signal_price") == current_price and state.get("last_signal_direction") == signal_direction:
        print("Segnale già notificato.")
        return

    state["last_signal_price"] = current_price
    state["last_signal_direction"] = signal_direction
    save_state(state)

    # 4. Invio Telegram
    emoji = "🟢" if signal_direction == "BUY" else "🔴"
    message = (
        f"{emoji} *SEGNALE STRUTTURALE XAU/USD* {emoji}\n\n"
        f"• *Ordine:* `{signal_direction}`\n"
        f"• *Lotti:* `{LOT_SIZE}`\n"
        f"• *Prezzo Attuale:* `{current_price}`\n\n"
        f"📊 *Analisi Indicatori:*\n"
        f"• *POC:* `{poc_price}`\n"
        f"• *Sweep Liquidity:* Il prezzo ha rotto il livello `{liq_low if signal_direction == 'BUY' else liq_high}`\n\n"
        f"🎯 *Take Profit (+3000 USD):* `{tp_price}`\n"
        f"🛑 *Stop Loss (-2700 USD):* `{sl_price}`\n\n"
        f"⚠️ *Nota Operativa:* Rispetta sempre i **${SL_DISTANCE}** di distanza dallo SL dal prezzo a cui entri a mercato!"
    )
    send_telegram_message(message)

if __name__ == "__main__":
    main()
