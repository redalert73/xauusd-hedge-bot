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

def calcola_rolling_vwap_e_bande(candles, index, periodo=50, num_std=3.0):
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

def main():
    print("🔄 Avvio Backtest VWAP Contrarian (Rolling SD 3.0 + Filtro Volume)...")
    candles = fetch_historical_data()
    if not candles:
        print("❌ Impossibile scaricare i dati storici.")
        return

    wins, losses, totale_operazioni = 0, 0, 0
    cooldown_index = 0

    for i in range(60, len(candles) - config.MAX_FUTURE_CANDLES):
        if i < cooldown_index:
            continue

        subset = candles[:i+1]
        current_candle = subset[-1]
        
        prezzo_chiusura = float(current_candle["close"])
        vwap, upper_band, lower_band = calcola_rolling_vwap_e_bande(candles, i, periodo=50, num_std=3.0)

        # Filtro sui volumi (richiede uno spike rispetto alla media mobile recente)
        volumi = [float(c.get("volume", 0)) for c in subset]
        vol_attuale = volumi[-1]
        vol_medio = sum(volumi[-21:-1]) / 20 if len(volumi) >= 21 else vol_attuale
        volume_confermato = vol_attuale >= (vol_medio * config.VOL_MULTIPLIER)

        segnale = None
        tp, sl = 0.0, 0.0

        # Ingresso condizionato da: Banda SD 3.0 + Chiusura oltre la banda + Spike di Volume
        if prezzo_chiusura >= upper_band and volume_confermato:
            segnale = "SELL"
            sl = prezzo_chiusura + config.SL_VAL
            tp = prezzo_chiusura - config.TP_VAL
        elif prezzo_chiusura <= lower_band and volume_confermato:
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
                        esito = "WIN"  # Raggiungimento SL
                        break
                    elif f_low <= tp:
                        esito = "LOSS" # Raggiungimento TP
                        break
                elif segnale == "BUY":
                    if f_low <= sl:
                        esito = "WIN"  # Raggiungimento SL
                        break
                    elif f_high >= tp:
                        esito = "LOSS" # Raggiungimento TP
                        break
            
            if esito == "WIN": wins += 1
            elif esito == "LOSS": losses += 1
            
            cooldown_index = i + candles_run

    print("\n===============================")
    print(f"📈 REPORT FINALE (VWAP Chirurgia Totale - SD 3.0 + Volume):")
    print(f"• Operazioni Totali: {totale_operazioni}")
    print(f"• Win (Raggiunto SL): {wins} | Loss (Raggiunto TP): {losses}")
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    print(f"• Win Rate: {win_rate:.2f}%")
    print("===============================")

if __name__ == "__main__":
    main()
