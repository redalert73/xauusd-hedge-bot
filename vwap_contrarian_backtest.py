import os
import requests
import math
from datetime import datetime
import config_breakout as config

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

def calcola_rolling_vwap_e_bande(candles, index, periodo=40, num_std=4.2): # Ottimizzato a 40 periodi e 4.2 SD
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
    
    if v_sum == 0 or not typical_prices:
        cl = float(candles[index]['close'])
        return cl, cl, cl

    vwap = p_v_sum / v_sum
    variance_sum = sum(v * ((tp - vwap) ** 2) for tp, v in typical_prices)
    std_dev = math.sqrt(variance_sum / v_sum) if v_sum > 0 else 0.0

    return vwap, vwap + (num_std * std_dev), vwap - (num_std * std_dev)

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

def main():
    print("🔄 Avvio Backtest VWAP Bilanciato (Periodo 40 + SD 4.2 + ATR 2.4)...")
    candles = fetch_historical_data()
    if not candles:
        print("❌ Impossibile scaricare i dati storici.")
        return

    wins, losses, totale_operazioni = 0, 0, 0
    cooldown_index = 0

    for i in range(60, len(candles) - config.MAX_FUTURE_CANDLES):
        if i < cooldown_index:
            continue

        current_candle = candles[i]
        prezzo_chiusura = float(current_candle["close"])
        prezzo_alto = float(current_candle["high"])
        prezzo_basso = float(current_candle["low"])
        range_candela = prezzo_alto - prezzo_basso

        vwap, upper_band, lower_band = calcola_rolling_vwap_e_bande(candles, i, periodo=40, num_std=4.2)
        atr = calcola_atr(candles, i, periodo=14)

        movimento_forte = range_candela >= (atr * 2.4) if atr > 0 else True

        segnale = None
        tp, sl = 0.0, 0.0

        if prezzo_chiusura >= upper_band and movimento_forte:
            segnale = "SELL"
            sl = prezzo_chiusura + config.SL_VAL
            tp = prezzo_chiusura - config.TP_VAL
        elif prezzo_chiusura <= lower_band and movimento_forte:
            segnale = "BUY"
            sl = prezzo_chiusura - config.SL_VAL
            tp = prezzo_chiusura + config.TP_VAL

        if segnale:
            totale_operazioni += 1
            esito = "SCADUTO"
            candles_run = 0

            for future_c_idx, future_c in enumerate(candles[i+1 : i + 1 + config.MAX_FUTURE_CANDLES]):
                candles_run = future_c_idx + 1
                f_high = float(future_c["high"])
                f_low = float(future_c["low"])
                
                if segnale == "SELL":
                    if f_high >= sl:
                        esito = "WIN"
                        break
                    elif f_low <= tp:
                        esito = "LOSS"
                        break
                elif segnale == "BUY":
                    if f_low <= sl:
                        esito = "WIN"
                        break
                    elif f_high >= tp:
                        esito = "LOSS"
                        break
            
            if esito == "WIN": wins += 1
            elif esito == "LOSS": losses += 1
            
            cooldown_index = i + candles_run

    print("\n===============================")
    print(f"📈 REPORT FINALE (VWAP Bilanciato Sweet-Spot):")
    print(f"• Operazioni Totali: {totale_operazioni}")
    print(f"• Win (Raggiunto SL): {wins} | Loss (Raggiunto TP): {losses}")
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    print(f"• Win Rate: {win_rate:.2f}%")
    print("===============================")

if __name__ == "__main__":
    main()
