import os
import sys
import requests

# Secrets da impostare nel repository GitHub (Settings > Secrets and variables > Actions)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_signal(direction: str, entry_price: float):
    if not BOT_TOKEN or not CHAT_ID:
        print("Errore: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID non configurati nei Secret di GitHub.")
        sys.exit(1)

    # Parametri fissi per XAU/USD a 1.04 lotti
    sl_distance = 25.96  # Target SL -$2.700 USD
    tp_distance = 28.85  # Target TP +$3.000 USD

    direction_clean = direction.upper().strip()

    if direction_clean == "BUY":
        sl = round(entry_price - sl_distance, 2)
        tp = round(entry_price + tp_distance, 2)
    elif direction_clean == "SELL":
        sl = round(entry_price + sl_distance, 2)
        tp = round(entry_price - tp_distance, 2)
    else:
        print(f"Direzione non valida: {direction}")
        sys.exit(1)

    message = (
        f"🚨 **SEGNALE OPERATIVO XAU/USD** 🚨\n\n"
        f"**Strumento:** XAUUSD\n"
        f"**Ordine:** {direction_clean}\n"
        f"**Lotti:** 1.04\n"
        f"**Ingresso:** {entry_price:.2f}\n"
        f"**Stop Loss:** {sl:.2f} (-$25.96)\n"
        f"**Take Profit:** {tp:.2f} (+$28.85)\n\n"
        f"⚠️ *Setup Target SL* - Inserimento immediato"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print(f"Segnale {direction_clean} inviato con successo a Telegram.")
    else:
        print(f"Errore invio Telegram: {response.text}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        input_direction = sys.argv[1]
        input_price = float(sys.argv[2])
        send_telegram_signal(input_direction, input_price)
    else:
        print("Uso: python xauusd_signal.py <BUY/SELL> <PREZZO>")
