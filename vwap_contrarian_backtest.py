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

def calcola_vwap_e_bande(candles, index, num_std=1.5):
    current_date = candles[index]['datetime'].split(' ')[0]
    p_v_sum, v_sum = 0.0, 0.0
    typical_prices = []
    
    for i in range(index, -1, -1):
        c_date = candles[i]['datetime'].split(' ')[0]
        if c_date != current_date:
            break
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

def main():
    print("🔄 Avvio Backtest Strategia VWAP Contrarian (Logica personalizzata SL=Win)...")
    candles = fetch_historical_data()
    if not candles:
        print("❌ Impossibile scaricare i dati storici.")
        return

    wins, losses, totale_operazioni = 0, 0, 0

    for i in range(50, len(candles) - config.MAX_FUTURE_CANDLES):
        subset = candles[:i+1]
        current_candle = subset[-1]
        
        prezzo_chiusura = float(current_candle["close"])
        prezzo_alto = float(current_candle["high"])
        prezzo_basso = float(current_candle["low"])

        vwap, upper_band, lower_band = calcola_vwap_e_bande(candles, i, num_std=1.5)

        segnale = None
        tp, sl = 0.0, 0.0

        # Logica Contrarian
        if prezzo_alto >= upper_band:
            segnale = "SELL"
            sl = prezzo_chiusura + config.SL_VAL
            tp = prezzo_chiusura - config.TP_VAL
        elif prezzo_basso <= lower_band:
            segnale = "BUY"
            sl = prezzo_chiusura - config.SL_VAL
            tp = prezzo_chiusura + config.TP_VAL

        if segnale:
            totale_operazioni += 1
            esito = "SCADUTO"

            for future_c in candles[i+1 : i + 1 + config.MAX_FUTURE_CANDLES]:
                f_high = float(future_c["high"])
                f_low = float(future_c["low"])
                
                if segnale == "SELL":
                    if f_high >= sl:
                        esito = "WIN"  # Raggiungere SL è il tuo obiettivo (WIN)
                        break
                    elif f_low <= tp:
                        esito = "LOSS" # Raggiungere TP è l'esito da evitare (LOSS)
                        break
                elif segnale == "BUY":
                    if f_low <= sl:
                        esito = "WIN"  # Raggiungere SL è il tuo obiettivo (WIN)
                        break
                    elif f_high >= tp:
                        esito = "LOSS" # Raggiungere TP è l'esito da evitare (LOSS)
                        break
            
            if esito == "WIN": wins += 1
            elif esito == "LOSS": losses += 1

    print("\n===============================")
    print(f"📈 REPORT FINALE (VWAP Contrarian Personalizzata):")
    print(f"• Operazioni Totali: {totale_operazioni}")
    print(f"• Win (Raggiunto SL): {wins} | Loss (Raggiunto TP): {losses}")
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    print(f"• Win Rate: {win_rate:.2f}%")
    print("===============================")

if __name__ == "__main__":
    main()
