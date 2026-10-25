import pandas as pd
import numpy as np
from backtest_liquidity_sweep_adaptive import run_adaptive_liquidity_sweep
from backtest_omnibus_adaptive import run_adaptive_omnibus

def fetch_market_data():
    """
    Simula o carica i dati storici delle candele per XAU/USD.
    Sostituisci questa funzione con il recupero dati reale (es. API Twelve Data o CSV).
    """
    # Generazione di dati di esempio robusti per il test di stress
    np.random.seed(42)
    date_rng = pd.date_range(start='2026-01-01', periods=200, freq='h')
    
    # Prezzo base XAU/USD attorno a 2300 con movimenti di volatilità
    base_price = 2300.0 + np.cumsum(np.random.randn(200) * 3.5)
    
    df = pd.DataFrame({
        'time': date_rng,
        'open': base_price + np.random.randn(200),
        'high': base_price + abs(np.random.randn(200) * 5),
        'low': base_price - abs(np.random.randn(200) * 5),
        'close': base_price + np.random.randn(200)
    })
    return df

def main():
    print("🚀 Avvio Master Orchestrator - XAU/USD Adaptive Stress Test...")
    
    # 1. Caricamento dati di mercato
    df_candles = fetch_market_data()
    
    print("\n--------------------------------------------------")
    print("🔹 Esecuzione Strategia 1: Adaptive Liquidity Sweep")
    print("--------------------------------------------------")
    results_sweep = run_adaptive_liquidity_sweep(
        df_candles=df_candles, 
        lot_size=1.04, 
        sl_usd=2200.0, 
        tp_usd=2000.0, 
        slippage_limit=2800.0,
        verbose=True
    )
    
    print("\n--------------------------------------------------")
    print("🔹 Esecuzione Strategia 2: Adaptive Omnibus")
    print("--------------------------------------------------")
    results_omnibus = run_adaptive_omnibus(
        df_candles=df_candles, 
        lot_size=1.04, 
        sl_usd=2200.0, 
        tp_usd=2000.0, 
        slippage_limit=2800.0,
        verbose=True
    )
    
    print("\n✅ Master Backtest completato con successo.")

if __name__ == "__main__":
    main()
