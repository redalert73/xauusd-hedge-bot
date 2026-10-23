import os
import requests
from datetime import datetime

def send_notification(message: str):
    """Invia notifiche simultaneamente su Telegram e/o ntfy.sh."""
    
    # 1. Telegram
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat_id:
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            payload = {"chat_id": tg_chat_id, "text": message, "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Errore invio Telegram: {e}")

    # 2. ntfy.sh
    ntfy_topic = os.getenv("NTFY_TOPIC")
    if ntfy_topic:
        try:
            url = f"https://ntfy.sh/{ntfy_topic}"
            requests.post(url, data=message.encode('utf-8'), timeout=5)
        except Exception as e:
            print(f"Errore invio ntfy: {e}")


def check_telegram_commands() -> bool:
    """Controlla se hai inviato un comando di stop (/stop o /pausa) su Telegram oggi."""
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not tg_token:
        return False

    try:
        url = f"https://api.telegram.org/bot{tg_token}/getUpdates"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return False
            
        data = response.json()
        if not data.get("ok"):
            return False

        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        # Cerca messaggi inviati nella giornata odierna
        for result in data.get("result", []):
            message = result.get("message", {})
            text = message.get("text", "").strip().lower()
            date_sent = message.get("date")
            
            if date_sent:
                msg_date = datetime.utcfromtimestamp(date_sent).strftime("%Y-%m-%d")
                if msg_date == today_str and text in ["/stop", "/pausa", "stop", "pausa"]:
                    return True
                    
    except Exception as e:
        print(f"Errore nella lettura dei comandi Telegram: {e}")
        
    return False
