import json
import os
import sys
from pathlib import Path
import requests

# Secrets impostati nel repository GitHub
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATE_PATH = Path("state/xauusd_state.json")

# Parametri fissi per 1.04 lotti su XAU/USD
SL_DISTANCE = 25.96  # Target SL -$2.700 USD
TP_DISTANCE = 28.85  # Target TP +$3.000 USD
LOOKBACK = 20        # Periodo per verificare rottura minimi/massimi

def load_state():
    if not STATE_PATH.exists():
        print(f"Errore: File {STATE_PATH} non trovato.")
        return None
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore lettura state JSON: {e}")
        return None

def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def send_telegram_signal(direction: str, entry_price: float) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("Errore: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID non configurati nei Secret di GitHub.")
        sys.exit(1)

    direction_clean = direction.upper().strip()

    if direction_clean == "BUY":
        sl = round(entry_price - SL_DISTANCE, 2)
        tp = round(entry_price + TP_DISTANCE, 2)
    elif direction_clean == "SELL":
        sl = round(entry_price + SL_DISTANCE, 2)
        tp = round(entry_price - TP_DISTANCE, 2)
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
        return True
    else:
        print(f"Errore invio Telegram: {response.text}")
        return False

def analyze_market_and_trigger():
    """Legge lo stato, calcola l'innesco Anti-Trend e aggiorna il file JSON."""
    state = load_state()
    if not state:
        return

    closes = state.get("closes", [])
    if len(closes) < LOOKBACK:
        print("Dati insufficienti nell'array 'closes' per analizzare il mercato.")
        return

    current_price = closes[-1]
    recent_closes = closes[-LOOKBACK:-1]
    donchian_high = max(recent_closes)
    donchian_low = min(recent_closes)

    signal_direction = None

    # LOGICA TARGET SL (ANTI-TREND):
    # 1. Compra se il prezzo crolla sotto i minimi receni -> l'inerzia spinge verso lo SL (-$25.96)
    if current_price < donchian_low:
        signal_direction = "BUY"
    # 2. Vendi se il prezzo esplode sopra i massimi recenti -> l'inerzia spinge verso lo SL (-$25.96)
    elif current_price > donchian_high:
        signal_direction = "SELL"

    if not signal_direction:
        print("Nessun breakout contrario rilevato. Nessun segnale da inviare.")
        return

    # Evita di inviare segnali duplicati per la stessa condizione
    signal_key = f"{signal_direction}-{round(current_price, 2)}"
    if state.get("last_signal_key") == signal_key:
        print("Segnale già inviato in precedenza per questa condizione.")
        return

    # Invia notifica e aggiorna lo stato
    if send_telegram_signal(signal_direction, current_price):
        state["last_signal_key"] = signal_key
        save_state(state)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # Modalità invio manuale da riga di comando
        input_direction = sys.argv[1]
        input_price = float(sys.argv[2])
        send_telegram_signal(input_direction, input_price)
    else:
        # Modalità automatica tramite analisi dello stato
        analyze_market_and_trigger()
