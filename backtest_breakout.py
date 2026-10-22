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

def main():
    print("🔄 Avvio Backtest Breakout Chirurgico (Donchian 30 + ATR 1.8 + SMA 50)...")
    candles = fetch_historical_data()
    if not candles:
        print("❌ Impossibile scaricare i dati storici.")
        return

    wins, losses, totale_operazioni = 0, 0, 0
    cooldown_index = 0
    
    periodo_donchian = 30  # Struttura Donchian estesa

    for i in range(50, len(candles) - config.MAX_FUTURE_CANDLES):
        if i < cooldown_index:
            continue

        subset = candles[:i+1]
        current_candle = subset[-1]
        
        prezzo_chiusura = float(current_candle["close"])
        prezzo_apertura = float(current_candle["open"])
        prezzo_alto = float(current_candle["high"])
        prezzo_basso = float(current_candle["low"])
        
        range_candela = prezzo_alto - prezzo_basso
        corpo_candela = abs(prezzo_chiusura - prezzo_apertura)

        # Calcolo massimi e minimi precedenti (Donchian 30)
        highest_prev = max(float(candles[x]["high"]) for x in range(i - periodo_donchian, i))
        lowest_prev = min(float(candles[x]["low"]) for x in range(i - periodo_donchian, i))

        # Filtro ATR Momentum
        atr = calcola_atr(candles, i, periodo=14)
        momentum_confermato = (range_candela >= (atr * 1.8)) and (corpo_candela >= (atr * 0.9)) if atr > 0 else True

        # Filtro Trend SMA 50
        sma_50 = calcola_sma(candles, i, periodo=50)
        trend_long = prezzo_chiusura > sma_50 if sma_50 > 0 else True
        trend_short = prezzo_chiusura < sma_50 if sma_50 > 0 else True

        segnale = None
        tp, sl = 0.0, 0.0

        if prezzo_chiusura > highest_prev and momentum_confermato and trend_long:
            segnale = "BUY"
            sl = prezzo_chiusura - config.SL_VAL
            tp = prezzo_chiusura + config.TP_VAL
        elif prezzo_chiusura < lowest_prev and momentum_confermato and trend_short:
            segnale = "SELL"
            sl = prezzo_chiusura + config.SL_VAL
            tp = prezzo_chiusura - config.TP_VAL

        if segnale:
            totale_operazioni += 1
            esito = "SCADUTO"
            candles_run = 0

            for future_c_idx, future_c in enumerate(candles[i+1 : i + 1 + config.MAX_FUTURE_CANDLES]):
                candles_run = future_c_idx + 1
                f_high = float(future_c["high"])
                f_low = float(future_c["low"])
                
                if segnale == "BUY":
                    if f_high >= tp:
                        esito = "WIN"
                        break
                    elif f_low <= sl:
                        esito = "LOSS"
                        break
                elif segnale == "SELL":
                    if f_low <= tp:
                        esito = "WIN"
                        break
                    elif f_high >= sl:
                        esito = "LOSS"
                        break
            
            if esito == "WIN": wins += 1
            elif esito == "LOSS": losses += 1
            
            cooldown_index = i + candles_run

    print("\n===============================")
    print(f"📈 REPORT FINALE (Breakout Chirurgico):")
    print(f"• Operazioni Totali: {totale_operazioni}")
    print(f"• Win: {wins} | Loss: {losses}")
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    print(f"• Win Rate: {win_rate:.2f}%")
    print("===============================")

if __name__ == "__main__":
    main()
