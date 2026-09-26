import os
import time
import requests
from datetime import datetime

# Configurazione API e Parametri
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "xauusd_signal_77ax")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

LOTS = 1.04  # Parametro rigido blindato

def fetch_market_data_with_retry(url, params, max_retries=3, delay=3):
    """Esegue chiamate API con sistema di retry automatico per evitare timeout."""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "values" in data:
                    return data
            print(f"⚠️ Tentativo {attempt}/{max_retries} fallito. Riprovo tra {delay}s...")
        except Exception as e:
            print(f"⚠️ Errore di connessione (Tentativo {attempt}): {e}")
        
        if attempt < max_retries:
            time.sleep(delay)
            delay *= 2
    return None

def invia_notifiche(direzione, prezzo, tp, sl, atr_val, swing_lvl):
    """Invia il segnale formattato su Telegram e ntfy con i dettagli tecnici."""
    emoji_dir = "🟢" if direzione == "BUY" else "🔴"
    
    message = (
        f"{emoji_dir} SEGNALE XAU/USD: {direzione} {emoji_dir}\n\n"
        f"• Lotti: {LOTS}\n"
        f"• Prezzo Ingresso: {prezzo:.2f}\n"
        f"• ATR Calcolato: {atr_val:.2f}\n"
        f"• Livello Swing/Liquidità: {swing_lvl:.2f}\n\n"
        f"🎯 Take Profit: {tp:.2f}\n"
        f"🛑 Stop Loss: {sl:.2f}"
    )

    print("Invio notifiche di segnale in corso...")

    # Invio Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url_tg = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload_tg = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }
        try:
            res = requests.post(url_tg, json=payload_tg, timeout=10)
            if res.status_code == 200:
                print("✅ Telegram: Segnale inviato con successo!")
            else:
                print(f"❌ Telegram Errore: {res.text}")
        except Exception as e:
            print(f"❌ Telegram Eccezione: {e}")

    # Invio ntfy.sh
    if NTFY_TOPIC:
        url_ntfy = f"https://ntfy.sh/{NTFY_TOPIC}"
        try:
            res = requests.post(
                url_ntfy,
                data=message.encode("utf-8"),
                headers={
                    "Title": f"Segnale XAU/USD - {direzione}",
                    "Tags": "chart_with_upwards_trend,bell" if direzione == "BUY" else "chart_with_downwards_trend,bell",
                    "Priority": "urgent",
                },
                timeout=10,
            )
            if res.status_code == 200:
                print(f"✅ ntfy.sh ({NTFY_TOPIC}): Segnale inviato con successo!")
            else:
                print(f"❌ ntfy Errore: {res.text}")
        except Exception as e:
            print(f"❌ ntfy Eccezione: {e}")

def is_orario_operativo():
    """Verifica che l'orario sia successivo alle 05:45 (apertura sessione asiatica/pre-Londra)."""
    now = datetime.now()
    ora_corrente = now.hour * 60 + now.minute
    inizio_operatività = 5 * 60 + 45  # 05:45
    return ora_corrente >= inizio_operatività

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Avvio check bot XAU/USD...")

    # 1. Controllo finestra oraria (dalle 05:45 in poi)
    if not is_orario_operativo():
        print("⏳ Fuori orario operativo (prima delle 05:45). Il bot termina senza azioni.")
        return

    print("🚀 Finestra attiva: analisi della liquidità asiatica e pre-Londra in corso...")

    # 2. Richiesta dati di mercato con retry
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 50,
        "apikey": TWELVE_DATA_API_KEY
    }
    
    data = fetch_market_data_with_retry(url, params)
    if not data:
        print("⚠️ Impossibile recuperare i dati da Twelve Data.")
        return

    # --- LOGICA DI CALCOLO (Inserisci qui i tuoi trigger ATR / Swing) ---
    segnale_trovato = False  # Diventa True se il prezzo rompe i livelli chiave
    direzione = "BUY"
    prezzo_attuale = 2350.00
    tp_val = 2375.00
    sl_val = 2314.00
    atr_val = 18.50
    swing_lvl = 2342.10

    # 3. Invio notifica se il segnale è confermato
    if segnale_trovato:
        invia_notifiche(direzione, prezzo_attuale, tp_val, sl_val, atr_val, swing_lvl)
    else:
        print("🔍 Nessun breakout o sweep di liquidità rilevato in questo intervallo.")

if __name__ == "__main__":
    main()
