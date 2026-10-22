import os
import requests
import math
from datetime import datetime
import config_breakout as config

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

def invia_notifica(messaggio):
    print(messaggio)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": messaggio, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"⚠️ Errore invio Telegram: {e}")
            
    if NTFY_TOPIC:
        url_ntfy = f"https://ntfy.sh/{NTFY_TOPIC}"
        try:
            requests.post(url_ntfy, data=messaggio.encode('utf-8'), timeout=10)
        except Exception as e:
            print(f"⚠️ Errore invio Ntfy: {e}")

def fetch_live_data():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": config.SYMBOL,
        "interval": config.INTERVAL,
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
        return 0.0
    tr_sum = 0.0
    for i in range(index - periodo + 1, index + 1):
        h = float(candles[i]['high'])
        l = float(candles[i]['low'])
        prev_cl = float(candles[i-1]['close']) if i > 0 else l
        tr = max(h - l, abs(h - prev_cl), abs(l - prev_cl))
        tr_sum += tr
    return tr_sum / periodo

def calcola_sma(candles, index, periodo=50):
    if index < periodo - 1:
        return 0.0
    somma = sum(float(candles[i]['close']) for i in range(index - periodo + 1, index + 1))
    return somma / periodo

def calcola_vwap_bande(candles, index, periodo=40, num_std=4.0):
    if index < periodo:
        cl = float(candles[index]['close'])
        return cl, cl, cl
    p_v_sum, v_sum = 0.0, 0.0
    typical_prices = []
    for i in range(index - periodo + 1, index + 1):
        h = float(candles[i]['high'])
        l = float(candles[i]['low'])
        cl = float(candles[i]['close'])
        v = float(candles[i].get('volume', 0))
        tp = (h + l + cl) / 3.0
        p_v_sum += tp * v
        v_sum += v
        typical_prices.append((tp, v))
    if v_sum == 0:
        cl = float(candles[index]['close'])
        return cl, cl, cl
    vwap = p_v_sum / v_sum
    variance_sum = sum(v * ((tp - vwap) ** 2) for tp, v in typical_prices)
    std_dev = math.sqrt(variance_sum / v_sum) if v_sum > 0 else 0.0
    return vwap, vwap + (num_std * std_dev), vwap - (num_std * std_dev)

def valuta_contrarian_vwap(candles):
    i = len(candles) - 1
    current = candles[i]
    p_close = float(current["close"])
    p_high = float(current["high"])
    p_low = float(current["low"])
    range_c = p_high - p_low

    atr = calcola_atr(candles, i, periodo=14)
    vwap, upper_b, lower_b = calcola_vwap_bande(candles, i, periodo=40, num_std=4.0)
    vwap_forte = range_c >= (atr * 2.2) if atr > 0 else True

    if p_close >= upper_b and vwap_forte:
        return ("CONTRARIAN VWAP", "SELL", p_close, p_close + config.SL_VAL, p_close - config.TP_VAL)
    elif p_close <= lower_b and vwap_forte:
        return ("CONTRARIAN VWAP", "BUY", p_close, p_close - config.SL_VAL, p_close + config.TP_VAL)
        
    return None

def valuta_breakout_elite(candles):
    i = len(candles) - 1
    periodo_donchian = 25
    if i < periodo_donchian:
        return None

    current = candles[i]
    p_close = float(current["close"])
    p_high = float(current["high"])
    p_low = float(current["low"])
    range_c = p_high - p_low

    atr = calcola_atr(candles, i, periodo=14)
    sma_50 = calcola_sma(candles, i, periodo=50)

    highest_prev = max(float(candles[x]["high"]) for x in range(i - periodo_donchian, i))
    lowest_prev = min(float(candles[x]["low"]) for x in range(i - periodo_donchian, i))
    breakout_forte = range_c >= (atr * 1.5) if atr > 0 else True
    trend_long = p_close > sma_50 if sma_50 > 0 else True
    trend_short = p_close < sma_50 if sma_50 > 0 else True

    if p_close > highest_prev and breakout_forte and trend_long:
        return ("BREAKOUT ELITE", "BUY", p_close, p_close - config.SL_VAL, p_close + config.TP_VAL)
    elif p_close < lowest_prev and breakout_forte and trend_short:
        return ("BREAKOUT ELITE", "SELL", p_close, p_close + config.SL_VAL, p_close - config.TP_VAL)

    return None

def main():
    print(f"🔍 Controllo Master Live: Contrarian VWAP & Breakout Elite ({config.SYMBOL} - {config.INTERVAL})...")
    candles = fetch_live_data()
    if not candles:
        print("❌ Impossibile recuperare i dati live.")
        return

    # 1. Valutazione Contrarian VWAP
    signal = valuta_contrarian_vwap(candles)
    
    # 2. Valutazione Breakout Elite (se VWAP non ha dato segnali)
    if not signal:
        signal = valuta_breakout_elite(candles)

    if signal:
        strat, dir_sig, prezzo, sl, tp = signal
        msg = (
            f"🚨 **SEGNALE MASTER: {strat}**\n"
            f"• Strumento: {config.SYMBOL}\n"
            f"• Direzione: **{dir_sig}**\n"
            f"• Ingresso: `{prezzo}`\n"
            f"• Stop Loss: `{sl}`\n"
            f"• Take Profit: `{tp}`\n"
            f"• Timestamp: `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC`"
        )
        invia_notifica(msg)
    else:
        print("💤 Nessun segnale attivo per Contrarian VWAP & Breakout Elite in questa candela.")

if __name__ == "__main__":
    main()
