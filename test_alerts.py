# ==========================================
# TEST NOTIFICHE TELEGRAM & NTFY
# ==========================================

import os
import requests

def test_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ [TELEGRAM] Variabili TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID non trovate.")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ [TELEGRAM] Messaggio di test inviato con successo!")
            return True
        else:
            print(f"❌ [TELEGRAM] Errore nell'invio: {response.text}")
            return False
    except Exception as e:
        print(f"❌ [TELEGRAM] Eccezione riscontrata: {e}")
        return False

def test_ntfy(message):
    topic = os.getenv("NTFY_TOPIC")
    
    if not topic:
        print("❌ [NTFY] Variabile NTFY_TOPIC non trovata.")
        return False
        
    url = f"https://ntfy.sh/{topic}"
    
    try:
        response = requests.post(
            url,
            data=message.encode('utf-8'),
            headers={
                "Title": "Test XAU/USD Bot",
                "Priority": "high",
                "Tags": "bell,chart_with_upwards_trend"
            }
        )
        if response.status_code == 200:
            print("✅ [NTFY] Notifica di test inviata con successo!")
            return True
        else:
            print(f"❌ [NTFY] Errore nell'invio: {response.text}")
            return False
    except Exception as e:
        print(f"❌ [NTFY] Eccezione riscontrata: {e}")
        return False

if __name__ == "__main__":
    print("==================================================")
    print("🔔 AVVIO TEST SISTEMA NOTIFICHE")
    print("==================================================")
    
    test_message = "🚀 *Test Segnale XAU/USD*\n- Lotto: 1.04\n- SL: -$2,400.0\n- TP: $2,000.0\n- Stato: Connessione verificata con successo!"
    
    test_telegram(test_message)
    test_ntfy("Test Segnale XAU/USD: Connessione ntfy verificata con successo!")
    
    print("==================================================")
