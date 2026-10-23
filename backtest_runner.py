import data_loader
from strategies import strategy_vwap, strategy_breakout, strategy_fibonacci
import pandas as pd

def run_backtest():
    print("==================================================")
    print("🔄 BACKTEST MULTI-STRATEGY MODULARE (XAU/USD)")
    print("==================================================")
    
    # 1. Download dei dati storici (24/7)
    df = data_loader.fetch_market_data()
    if df.empty:
        print("❌ Impossibile recuperare i dati storici per il backtest.")
        return

    print(f"✅ Dati storici caricati correttamente ({len(df)} candele).")
    print(f"🕒 Applicazione filtri orari operativi definiti in config.py...\n")

    # 2. Esecuzione delle strategie (i moduli filtrano automaticamente i segnali fuori orario)
    signals = []
    signals.extend(strategy_vwap.run(df))
    signals.extend(strategy_breakout.run(df))
    signals.extend(strategy_fibonacci.run(df))

    # 3. Ordinamento cronologico dei segnali
    signals.sort(key=lambda x: x[0])

    # 4. Calcolo metriche e statistiche di backtest
    num_days = max(1, (df["datetime"].max() - df["datetime"].min()).days)
    avg_signals_per_day = len(signals) / num_days

    print(f"📊 REPORT STATISTICO BACKTEST (Periodo: ~{num_days} giorni)")
    print("--------------------------------------------------")
    print(f" - Totale Segnali in Orario Consentito: {len(signals)}")
    print(f" - Frequenza Media Segnali al Giorno: {avg_signals_per_day:.2f}")
    print("--------------------------------------------------")
    print("🔍 ULTIMI SEGNALI RILEVATI NEL BACKTEST:")
    
    # Mostra gli ultimi 10 segnali per un riscontro rapido
    for dt, label, price in signals[-10:]:
        print(f"[{dt}] {label} | Prezzo: {price}")
        
    print("==================================================")

if __name__ == "__main__":
    run_backtest()
