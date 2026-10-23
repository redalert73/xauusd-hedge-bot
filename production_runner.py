# ==========================================
# PRODUCTION RUNNER - XAU/USD MULTI-STRATEGY
# ==========================================

import os
import time
import pandas as pd
import requests
from datetime import datetime

# Import delle strategie
from strategies import strategy_breakout, strategy_vwap, strategy_fibonacci

def send_telegram_alert(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Telegram: Credenziali non configurate.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if not response.json().get("ok"):
            print(f"❌ Telegram Error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram Exception: {e}")

def send_ntfy_alert(title, message):
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        print("❌ ntfy: Topic non configurato.")
        return
        
    url = f"https://ntfy.sh/{topic}"
    try:
        requests.post(
            url,
            data=message.encode('utf-8'),
            headers={
                "Title": title,
                "Priority": "high",
                "Tags": "chart_with_upwards_trend,bell"
            },
            timeout=10
        )
    except Exception as e:
        print(f"❌ ntfy Exception: {e}")

def fetch_live_data():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("❌ ERRORE: TWELVE_DATA_API_KEY non trovata.")
        return None
        
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=100&apikey={api_key}&timezone=UTC"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if "values" not in data:
            print(f"❌ Errore API Twelve Data: {data}")
            return None
            
        df = pd.DataFrame(data["values"])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        return df
    except Exception as e:
        print(f"❌ Errore di connessione a Twelve Data: {e}")
        return None

def run_production():
    print("=" * 50)
    print("🚀 PRODUCTION RUNNER - XAU/USD LIVE CHECK")
    print("=" * 50)
    
    df = fetch_live_data()
    if df is None or df.empty:
        print("❌ Impossibile recuperare i dati di mercato.")
        return
        
    strategies_registry = {
        "Breakout Elite": strategy_breakout,
        "VWAP Strategy": strategy_vwap,
        "Fibonacci Strategy": strategy_fibonacci
    }
    
    active_signals = []
    
    for strat_name, strat_module in strategies_registry.items():
        signals = strat_module.run(df)
        if signals:
            # Prende l'ultimo segnale generato dalla strategia
            latest_time, latest_type, latest_price = signals[-1]
            active_signals.append({
                "strategy": strat_name,
                "time": latest_time,
                "type": latest_type,
                "price": latest_price
            })
            
    if active_signals:
        print(f"🔥 Rilevati {len(active_signals)} segnali attivi!")
        for sig in active_signals:
            msg = (
                f"🚨 *SEGNALE XAU/USD - {sig['strategy'].upper()}*\n\n"
                f"• *Direzione:* `{sig['type']}`\n"
                f"• *Prezzo:* `${sig['price']:.2f}`\n"
                f"• *Orario (UTC):* `{sig['time']}`\n\n"
                f"⚠️ Azione richiesta: Verifica terminale e seleziona il trade."
            )
            print(msg)
            send_telegram_alert(msg)
            send_ntfy_alert(f"Segnale {sig['strategy']}", f"{sig['type']} @ {sig['price']:.2f}")
    else:
        print("ℹ️ Nessun nuovo segnale attivo nell'ultima candela analizzata.")
        
    print("=" * 50)
    print("✅ CHECK DI PRODUZIONE COMPLETATO")
    print("=" * 50)

if __name__ == "__main__":
    run_production()
