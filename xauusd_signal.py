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

def is_orario_operativo():
    """Verifica se siamo nella finestra oraria consentita (dalle 05:45 in poi)."""
    now = datetime.now()
    ora_corrente = now.hour * 60 + now.minute
    inizio_operatività = 5 * 60 + 45  # 05:45
    
    # Restituisce True se sono passate le 05:45 (puoi aggiungere un limite di chiusura se serve)
    return ora_corrente >= inizio_operatività

def esegui_controllo_mercato():
    if not is_orario_operativo():
        print("⏳ Fuori orario operativo (prima delle 05:45). Il bot è in attesa...")
        return False

    print("🚀 Finestra operativa attiva: analisi ATR e liquidità in corso...")
    # Qui inserisci la tua logica esistente di calcolo dei prezzi, ATR e swing
    return True

def main_loop():
    """Esegue controlli multipli a intervalli regolari mentre il PC è acceso."""
    print("🤖 Bot XAU/USD avviato. Monitoraggio attivo...")
    
    while True:
        try:
            if esegui_controllo_mercato():
                # Esegue l'analisi e invia il segnale se le condizioni sono verificate
                pass
        except Exception as e:
            print(f"❌ Errore nel ciclo principale: {e}")
            
        # Attende 15 minuti prima del prossimo controllo (puoi regolarlo a piacimento)
        time.sleep(900) 

if __name__ == "__main__":
    main_loop()
    
