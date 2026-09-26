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

def calcola_atr(candles, periodo=14):
    """Calcola l'ATR (Average True Range) reale dalle ultime candele."""
    if len(candles) < periodo + 1:
        return 15.0
    
    tr_list = []
    for i in range(periodo):
        high = float(candles[i]['high'])
        low = float(candles[i]['low'])
        close_prev = float(candles[i+1]['close'])
        
        tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
        tr_list.append(tr)
        
    return sum(tr_list) / len(tr_list)

def calcola_ema(closes, periodo):
    """Calcola la Media Mobile Esponenziale (EMA) per un dato periodo."""
    if len(closes) < periodo:
        return closes[0]
    
    multiplier = 2 / (periodo + 1)
    ema = sum(closes[:periodo]) / periodo
    
    for close in reversed(closes[periodo:]):
        ema = (close - ema) * multiplier + ema
        
    return ema

def invia_notifiche(direzione, prezzo, tp, sl, atr_val, swing_lvl, ema20, ema30, ema100):
    """Invia il segnale formattato su Telegram e ntfy con i dettagli tecnici e delle EMA."""
    emoji_dir = "🟢" if direzione == "BUY" else "🔴"
    
    message = (
        f"{emoji_dir} SEGNALE XAU/USD (INVERSO): {direzione} {emoji_dir}\n\n"
        f"• Lotti: {LOTS}\n"
        f"• Prezzo Ingresso: {prezzo:.2f}\n"
        f"• ATR Dinamico: {atr_val:.2f}\n"
        f"• Livello Swing: {swing_lvl:.2f}\n\n"
        f"📈 Filtri EMA:\n"
        f"  - EMA 20: {ema20:.2f}\n"
        f"  - EMA 30: {ema30:.2f}\n"
        f"  - EMA 100: {ema100:.2f}\n\n"
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
                    "Title": f"Segnale XAU/USD Inverso - {direzione}",
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
    """Verifica che l'orario sia successivo alle 05:45."""
    now = datetime.now()
    ora_corrente = now.hour * 60 + now.minute
    return ora_corrente >= (5 * 60 + 45)

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Avvio check bot XAU/USD (Logica Inversa)...")

    if not is_orario_operativo():
        print("⏳ Fuori orario operativo (prima delle 05:45). Il bot termina senza azioni.")
        return

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 120,
        "apikey": TWELVE_DATA_API_KEY
    }
    
    data = fetch_market_data_with_retry(url, params)
    if not data or "values" not in data:
        print("⚠️ Impossibile recuperare i dati da Teve Data.")
        return

    candles = data["values"]
    prezzo_attuale = float(candles[0]["close"])
    closes = [float(c["close"]) for c in reversed(candles)]

    atr_val = calcola_atr(candles, periodo=14)
    ema_20 = calcola_ema(closes, 20)
    ema_30 = calcola_ema(closes, 30)
    ema_100 = calcola_ema(closes, 100)
    
    highs = [float(c["high"]) for c in candles[1:17]]
    lows = [float(c["low"]) for c in candles[1:17]]
    swing_high = max(highs)
    swing_low = min(lows)

    print(f"📊 Prezzo: {prezzo_attuale:.2f} | Swing High: {swing_high:.2f} | Swing Low: {swing_low:.2f}")

    segnale_trovato = False
    direzione = ""
    tp_val = 0.0
    sl_val = 0.0
    swing_lvl_segnale = 0.0

    # LOGICA INVERSA:
    # 1. Se il prezzo supera il massimo, ci aspettiamo un’inversione/ritracciamento -> VENDITA (SELL)
    if prezzo_attuale > swing_high and (prezzo_attuale - swing_high) > (atr_val * 0.2):
        segnale_trovato = True
        direzione = "SELL"
        swing_lvl_segnale = swing_high
        sl_val = prezzo_attuale + (atr_val * 1.5)  # Stop Loss sopra
        tp_val = prezzo_attuale - (atr_val * 3.0)  # Take Profit sotto

    # 2. Se il prezzo scende sotto il minimo, ci aspettiamo un rimbalzo -> ACQUISTO (BUY)
    elif prezzo_attuale < swing_low and (swing_low - prezzo_attuale) > (atr_val * 0.2):
        segnale_trovato = True
        direzione = "BUY"
        swing_lvl_segnale = swing_low
        sl_val = prezzo_attuale - (atr_val * 1.5)  # Stop Loss sotto
        tp_val = prezzo_attuale + (atr_val * 3.0)  # Take Profit sopra

    if segnale_trovato:
        invia_notifiche(direzione, prezzo_attuale, tp_val, sl_val, atr_val, swing_lvl_segnale, ema_20, ema_30, ema_100)
    else:
        print("🔍 Nessun segnale inverso valido rilevato in questo intervallo.")

if __name__ == "__main__":
    main()
