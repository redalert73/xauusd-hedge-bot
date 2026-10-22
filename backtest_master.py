# backtest_master.py

import os
import requests
import math
from datetime import datetime
import config

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

def fetch_historical_data():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": config.SYMBOL,
        "interval": config.INTERVAL,
        "outputsize": 1000,
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

def verifica_orario(datetime_str):
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        minuti_correnti = dt.hour * 60 + dt.minute
        return config.ORA_INIZIO_MINUTI <= minuti_correnti <= config.ORA_FINE_MINUTI
    except Exception:
        return True

def valuta_esito(candles, start_idx, segnale, sl, tp):
    for future_c in candles[start_idx+1 : start_idx + 1 + config.MAX_FUTURE_CANDLES]:
        f_high = float(future_c["high"])
        f_low = float(future_c["low"])
        # Logica personalizzata: Win = Raggiunto SL, Loss = Raggiunto TP
        if segnale == "SELL":
            if f_high >= sl: return "WIN"
            elif f_low <= tp: return "LOSS"
        elif segnale == "BUY":
            if f_low <= sl: return "WIN"
            elif f_high >= tp: return "LOSS"
    return "SCADUTO"

def main():
    print(f"🔄 Avvio Backtest Master: Contrarian VWAP & Breakout Elite ({config.SYMBOL} - {config.INTERVAL})...")
    candles = fetch_historical_data()
    if not candles:
        print("❌ Impossibile scaricare i dati storici.")
        return

    wins, losses, totale_operazioni = 0, 0, 0
    cooldown_index = 0
    periodo_donchian = 25

    for i in range(50, len(candles) - config.MAX_FUTURE_CANDLES):
        if i < cooldown_index:
            continue

        current_candle = candles[i]
        if not verifica_orario(current_candle.get("datetime", "")):
            continue

        p_close = float(current_candle["close"])
        p_high = float(current_candle["high"])
        p_low = float(current_candle["low"])
        range_c = p_high - p_low

        atr = calcola_atr(candles, i, periodo=config.ATR_PERIOD)
        sma_50 = calcola_sma(candles, i, periodo=50)

        segnale = None
        tp, sl = 0.0, 0.0

        # 1. Controllo Contrarian VWAP
        vwap, upper_b, lower_b = calcola_vwap_bande(candles, i, periodo=40, num_std=4.0)
        vwap_forte = range_c >= (atr * config.VOL_MULTIPLIER) if atr > 0 else True

        if p_close >= upper_b and vwap_forte:
            segnale = "SELL"
            sl = p_close + config.SL_VAL
            tp = p_close - config.TP_VAL
        elif p_close <= lower_b and vwap_forte:
            segnale = "BUY"
            sl = p_close - config.SL_VAL
            tp = p_close + config.TP_VAL

        # 2. Controllo Breakout Elite (se VWAP non ha dato segnale)
        if not segnale and i >= periodo_donchian:
            highest_prev = max(float(candles[x]["high"]) for x in range(i - periodo_donchian, i))
            lowest_prev = min(float(candles[x]["low"]) for x in range(i - periodo_donchian, i))
            
            breakout_forte = range_c >= (atr * config.MOM_MULTIPLIER * 3) if atr > 0 else True
            trend_long = p_close > sma_50 if sma_50 > 0 else True
            trend_short = p_close < sma_50 if sma_50 > 0 else True

            if p_close > highest_prev and breakout_forte and trend_long:
                segnale = "BUY"
                sl = p_close - config.SL_VAL
                tp = p_close + config.TP_VAL
            elif p_close < lowest_prev and breakout_forte and trend_short:
                segnale = "SELL"
                sl = p_close + config.SL_VAL
                tp = p_close - config.TP_VAL

        if segnale:
            totale_operazioni += 1
            esito = valuta_esito(candles, i, segnale, sl, tp)
            if esito == "WIN":
                wins += 1
            elif esito == "LOSS":
                losses += 1
            
            # Cooldown per evitare overtrading
            cooldown_index = i + 3

    print("\n======================================================")
    print(f"📈 REPORT FINALE BACKTEST: Contrarian VWAP & Breakout Elite")
    print(f"• Operazioni Totali: {totale_operazioni}")
    print(f"• Win (Raggiunto SL): {wins} | Loss (Raggiunto TP): {losses}")
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    print(f"• Win Rate: {win_rate:.2f}%")
    print("========================================================")

if __name__ == "__main__":
    main()
