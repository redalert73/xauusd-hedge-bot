import json
import os
import requests

# Parametri e Costanti
STATE_FILE = "state/xauusd_state.json"
SL_DISTANCE = 25.96  # Produce lo Stop Loss di -$2.700 USD su 1.04 lotti
TP_DISTANCE = 28.85  # Produce il Take Profit di +$3.000 USD su 1.04 lotti
LOT_SIZE = 1.04

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")


def fetch_latest_gold_price():
    """Recupera il prezzo Spot reale di XAU/USD da Twelve Data API in tempo reale."""
    if not TWELVE_DATA_API_KEY:
        print(
            "ERRORE: Manca la chiave TWELVE_DATA_API_KEY nei Secrets di GitHub."
        )
        return None

    url = f"https://api.twelvedata.com/price?symbol=XAU/USD&apikey={TWELVE_DATA_API_KEY}"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if "price" in data:
            price = round(float(data["price"]), 2)
            return price
        else:
            print(f"Errore risposta API Twelve Data: {data}")
            return None
    except Exception as e:
        print(f"Errore durante la connessione all'API Twelve Data: {e}")
        return None


def load_and_update_state(price):
    """Carica lo stato attuale e aggiunge il nuovo prezzo memorizzando fino a 50 candele."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    state = {
        "closes": [],
        "last_signal_price": None,
        "last_signal_direction": None,
    }

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except json.JSONDecodeError:
            pass

    closes = state.get("closes", [])
    if price is not None:
        closes.append(price)
        closes = closes[-50:]  # Mantiene fino alle ultime 50 letture
        state["closes"] = closes

    return state


def save_state(state):
    """Salva lo stato aggiornato nel file JSON."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


def send_telegram_message(message):
    """Invia il messaggio di segnale al canale/chat Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(
            "ERRORE: Credentials Telegram assenti nelle variabili d'ambiente."
        )
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("Notifica Telegram inviata correttamente!")
        else:
            print(f"Errore invio Telegram: {res.text}")
    except Exception as e:
        print(f"Eccezione durante la connessione a Telegram: {e}")


def main():
    # 1. Recupera il prezzo spot in tempo reale
    current_price = fetch_latest_gold_price()
    if current_price is None:
        print("Impossibile procedere senza prezzo di mercato spot aggiornato.")
        return

    print(f"Prezzo corrente XAU/USD Spot registrato: {current_price}")

    # 2. Aggiorna e salva la cronologia
    state = load_and_update_state(current_price)
    save_state(state)

    closes = state.get("closes", [])

    if len(closes) < 20:
        print(
            f"Storico insufficiente per il Donchian Channel ({len(closes)}/20). In attesa di nuove esecuzioni."
        )
        return

    # 3. Calcolo Donchian sui 19 periodi precedenti
    previous_closes = closes[-20:-1]
    donchian_low = min(previous_closes)
    donchian_high = max(previous_closes)

    print(
        f"Donchian Low (19p): {donchian_low} | Donchian High (19p): {donchian_high}"
    )

    signal_direction = None
    sl_price = 0.0
    tp_price = 0.0

    # 4. Logica Anti-Trend
    if current_price < donchian_low:
        signal_direction = "BUY"
        sl_price = round(current_price - SL_DISTANCE, 2)
        tp_price = round(current_price + TP_DISTANCE, 2)
    elif current_price > donchian_high:
        signal_direction = "SELL"
        sl_price = round(current_price + SL_DISTANCE, 2)
        tp_price = round(current_price - TP_DISTANCE, 2)
    else:
        print("Prezzo all'interno del range: nessun breakout contrario.")
        return

    # 5. Evita messaggi duplicati sullo stesso livello
    if (
        state.get("last_signal_price") == current_price
        and state.get("last_signal_direction") == signal_direction
    ):
        print("Segnale già notificato in precedenza per questo valore.")
        return

    # Salva il nuovo segnale nello stato
    state["last_signal_price"] = current_price
    state["last_signal_direction"] = signal_direction
    save_state(state)

    # 6. Formattazione e invio
    emoji = "🟢" if signal_direction == "BUY" else "🔴"
    message = (
        f"{emoji} *SEGNALE ANTI-TREND XAU/USD* {emoji}\n\n"
        f"• *Ordine:* `{signal_direction}`\n"
        f"• *Lotti:* `{LOT_SIZE}`\n"
        f"• *Prezzo Segnale (Spot):* `{current_price}`\n\n"
        f"🎯 *Take Profit (+3000 USD):* `{tp_price}` (+${TP_DISTANCE})\n"
        f"🛑 *Stop Loss (-2700 USD):* `{sl_price}` (-${SL_DISTANCE})\n\n"
        f"⚠️ *Istruzione Istantanea:* Apri subito l'ordine a mercato. "
        f"Se il prezzo varia prima dell'ingresso, rispetta sempre **${SL_DISTANCE}** di distanza dallo SL dal prezzo a cui sei entrato!"
    )

    send_telegram_message(message)


if __name__ == "__main__":
    main()
