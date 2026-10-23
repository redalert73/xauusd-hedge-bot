# ==========================================
# PRODUCTION RUNNER - XAU/USD LIVE SIGNALS
# ==========================================

import os
import pandas as pd
import requests
from datetime import datetime

# Import delle strategie
from strategies import strategy_breakout, strategy_vwap, strategy_fibonacci

def send_notification(message):
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            requests.post(url, json={"chat_id": tg_chat, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"⚠️ Errore invio Telegram: {e}")
            
    ntfy_topic = os.getenv("NTFY_TOPIC")
    if ntfy_topic:
        try:
            requests.post(f"https://ntfy.sh/{ntfy_topic}", data=message.encode('utf-8'))
        except Exception as e:
            print(f"⚠️ Errore invio ntfy: {e}")

def download_twelve_data():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("❌ ERRORE: TWELVE_DATA_API_KEY non trovata.")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=100&apikey={api_key}&timezone=UTC"
    response = requests.get(url)
    data = response.json()
    
    if "values" not in data:
        return None
        
    df = pd.DataFrame(data["values"])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def run_production():
    print("🔄 Esecuzione Production Runner (XAU/USD)...")
    df = download_twelve_data()
    if df is None or df.empty:
        return
        
    last_time = df.index[-1]
    
    # Filtro sessione operativa (08:00 - 19:00 UTC)
    if last_time.hour < 8 or last_time.hour >= 19:
        print(f"⏸ Fuori dalla sessione attiva ({last_time}). Nessun segnale inviato.")
        return

    strategies_registry = {
        "Breakout Elite": strategy_breakout,
        "VWAP Strategy": strategy_vwap,
        "Fibonacci Strategy": strategy_fibonacci
    }
    
    lot_size = 1.04
    sl_usd = -2400.0  # Impatto contabile rigoroso sull'SL
    
    for strat_name, strat_module in strategies_registry.items():
        signals = strat_module.run(df)
        if not signals:
            continue
            
        latest_signal = signals[-1]
        sig_time, sig_type, sig_price = latest_signal
        
        # Controlla se il segnale appartiene all'ultima candela
        if sig_time == last_time:
            msg = (
                f"🚨 **SEGNALE LIVE - {strat_name.upper()}** 🚨\n\n"
                f"🔹 Coppia: XAU/USD (5min)\n"
                f"🔹 Tipo: `{sig_type}`\n"
                f"🔹 Prezzo: `{sig_price}`\n"
                f"🔹 Lotto: `{lot_size}`\n"
                f"🔹 Target Previsto (SL): `{sl_usd:,.2f} USD`\n"
                f"🔹 Timestamp: `{sig_time}`"
            )
            print(f"📢 Invio notifica per {strat_name}...")
            send_notification(msg)

if __name__ == "__main__":
    run_production()
