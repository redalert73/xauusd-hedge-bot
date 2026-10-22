import os
import requests
from datetime import datetime

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

def fetch_historical_data():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": "15min",
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

def main():
    print("🔄 Avvio Backtest XAU/USD (SL 2.300 + Filtri Ultra-Rigidi)...")
    candles = fetch_historical_data()
    if not candles:
        print("❌ Impossibile scaricare i dati storici.")
        return

    print(f"📊 Totale candele caricate per l'analisi: {len(candles)}")
    
    wins = 0
    losses = 0
    totale_operazioni = 0

    SL_VAL = 2.300  # Modificato a 2.300
    TP_VAL = 2.000

    for i in range(120, len(candles) - 10):
        subset = candles[:i+1]
        current_candle = subset[-1]
        
        if not is_orario_consentito(current_candle["datetime"]):
            continue

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

        # Filtri di ingresso ultra-rigidi
        volume_confermato = vol_attuale >= (vol_medio * 1.8)
        momentum_valido = abs(prezzo_attuale - apertura_attuale) >= (atr_val * 0.45)
        estensione_valida = abs(prezzo_attuale - ema_20) >= (atr_val * 0.4)

        segnale = None
        tp = 0.0
        sl = 0.0

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
            totale_operazioni += 1
            esito = "IN_CORSO"
            for future_c in candles[i+1 : i+15]:
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
            
            if esito == "WIN":
                wins += 1
            elif esito == "LOSS":
                losses += 1

            print(f"[{current_candle['datetime']}] Segnale: {segnale} @ {prezzo_attuale:.2f} | Esito: {esito}")

    print("\n===============================")
    print(f"📈 REPORT FINALE BACKTEST (SL 2.300 / Ultra-Rigidi):")
    print(f"• Operazioni Totali: {totale_operazioni}")
    print(f"• Win (Prese SL): {wins}")
    print(f"• Loss (Prese TP): {losses}")
    win_rate = (wins / totale_operazioni * 100) if totale_operazioni > 0 else 0
    print(f"• Win Rate: {win_rate:.2f}%")
    print("===============================")

if __name__ == "__main__":
    main()
