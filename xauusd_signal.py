import os
import requests
from datetime import datetime

# Credenziali da Variabili d'Ambiente (GitHub Secrets)
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

STATE_FILE = "last_signal.txt"

def fetch_latest_data():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
        "outputsize": 100,
        "apikey": TWELVE_DATA_API_KEY
    }
    response = requests.get(url, params=params, timeout=15)
    if response.status_code == 200:
        data = response.json()
        if "values" in data:
            return list(reversed(data["values"]))
    return []

def calcola_atr(candles, index, periodo=14):
    if index < periodo:
        return 15.0
    tr_list = []
    for i in range(index - periodo + 1, index + 1):
        high = float(candles[i]['high'])
        low = float(candles[i]['low'])
        close_prev = float(candles[i-1]['close'])
        tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
        tr_list.append(tr)
    return sum(tr_list) / len(tr_list)

def calcola_ema(closes, periodo):
    if len(closes) < periodo:
        return closes[0]
    multiplier = 2 / (periodo + 1)
    ema = sum(closes[:periodo]) / periodo
    for close in closes[periodo:]:
        ema = (close - ema) * multiplier + ema
    return ema

def is_orario_consentito(datetime_str):
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    ora_minuti = dt.hour * 60 + dt.minute
    inizio = 5 * 60 + 45   # 05:45
    fine = 20 * 60         # 20:00
    return inizio <= ora_minuti <= fine

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Credenziali Telegram mancanti.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Errore invio Telegram: {e}")

def send_ntfy(title, message):
    if not NTFY_TOPIC:
        print("⚠️ Topic ntfy mancante.")
        return
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    try:
        requests.post(
            url,
            data=message.encode('utf-8'),
            headers={
                "Title": title,
                "Priority": "high",
                "Tags": "chart_with_upwards_trend,moneybag"
            },
            timeout=10
        )
    except Exception as e:
        print(f"❌ Errore invio ntfy: {e}")

def main():
    print("🚀 Controllo segnali live XAU/USD (Configurazione Definitiva)...")
    candles = fetch_latest_data()
    if not candles:
        print("❌ Impossibile scaricare i dati da Twelve Data.")
        return

    # Analizziamo la penultima candela chiusa per sicurezza operativa
    i = len(candles) - 2
    current_candle = candles[i]
    datetime_str = current_candle["datetime"]

    # Controllo duplicati tramite file di stato
    last_notified = ""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            last_notified = f.read().strip()

    if datetime_str == last_notified:
        print(f"ℹ️ Segnale per la candela {datetime_str} già notificato. Uscita.")
        return

    if not is_orario_consentito(datetime_str):
        print(f"⏰ {datetime_str} fuori dall'orario operativo (05:45 - 20:00).")
        return

    subset = candles[:i+1]
    prezzo_attuale = float(current_candle["close"])
    apertura_attuale = float(current_candle["open"])
    closes = [float(c["close"]) for c in subset]
    
    volumi = [float(c.get("volume", 0)) for c in subset]
    vol_attuale = volumi[-1]
    vol_medio = sum(volumi[-21:-1]) / 20 if len(volumi) >= 21 else vol_attuale

    atr_val = calcola_atr(subset, i, periodo=14)
    ema_20 = calcola_ema(closes, 20)
    ema_30 = calcola_ema(closes, 30)

    highs = [float(c["high"]) for c in subset[-17:-1]]
    lows = [float(c["low"]) for c in subset[-17:-1]]
    swing_high = max(highs)
    swing_low = min(lows)

    # Filtri Ultra-Rigidi
    volume_confermato = vol_attuale >= (vol_medio * 1.8)
    momentum_valido = abs(prezzo_attuale - apertura_attuale) >= (atr_val * 0.45)
    estensione_valida = abs(prezzo_attuale - ema_20) >= (atr_val * 0.4)

    segnale = None
    tp = 0.0
    sl = 0.0
    
    # PARAMETRI DEFINITIVI VALIDATI
    SL_VAL = 2.300
    TP_VAL = 2.000

    if prezzo_attuale > swing_high and (prezzo_attuale - swing_high) > (atr_val * 0.2):
        if volume_confermato and momentum_valido and estensione_valida and ema_20 > ema_30:
            segnale = "SELL"
            sl = prezzo_attuale + SL_VAL
            tp = prezzo_attuale - TP_VAL

    elif prezzo_attuale < swing_low and (swing_low - prezzo_attuale) > (atr_val * 0.2):
        if volume_confermato and momentum_valido and estensione_valida and ema_20 < ema_30:
            segnale = "BUY"
            sl = prezzo_attuale - SL_VAL
            tp = prezzo_attuale + TP_VAL

    if segnale:
        msg = (
            f"🚨 **NUOVO SEGNALE XAU/USD** 🚨\n\n"
            f"• **Direzione:** `{segnale}`\n"
            f"• **Prezzo:** `{prezzo_attuale:.2f}`\n"
            f"• **Orario:** `{datetime_str}`\n"
            f"• **Stop Loss (WIN):** `{sl:.2f}`\n"
            f"• **Take Profit (LOSS):** `{tp:.2f}`\n\n"
            f"⚙️ *Filtri: Vol 1.8x | Mom 0.45 ATR | SL 2.300*"
        )
        print(msg)
        send_telegram(msg)
        send_ntfy(f"Segnale XAU/USD: {segnale}", msg)

        # Salva lo stato per evitare notifiche doppie
        with open(STATE_FILE, "w") as f:
            f.write(datetime_str)
    else:
        print(f"📊 {datetime_str} - Nessun setup valido riscontrato.")

if __name__ == "__main__":
    main()
