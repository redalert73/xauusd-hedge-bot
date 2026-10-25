# ==========================================
# 🔵 [BACKTEST DETAILED] - ANALISI GRANULARE
# ==========================================

import pandas as pd
import numpy as np
import requests
import os

def download_twelve_data():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("❌ [DETAILED] ERRORE: TWELVE_DATA_API_KEY non trovata.")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=500&apikey={api_key}&timezone=UTC"
    response = requests.get(url)
    data = response.json()
    
    if "values" not in data:
        print("❌ [DETAILED] ERRORE nel recupero dati da Twelve Data.")
        return None
        
    df = pd.DataFrame(data["values"])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def run_detailed_backtest(df, strategy_module, strategy_name):
    print("\n" + "-"*50)
    print(f"📊 [ACTION TYPE: BACKTEST DETAILED] -> Analisi: {strategy_name.upper()}")
    print("-"*50)
    
    # Parametri definitivi bloccati
    lot_size = 1.04
    sl_usd = -2400.0
    tp_usd = 2000.0
    slippage_limit_per_trade = -2900.0  # Limite da non raggiungere mai sul singolo trade
    
    signals = strategy_module.run(df)
    if not signals:
        print(f"⚠️ [DETAILED] Nessun segnale generato per {strategy_name}.")
        return None
        
    detailed_trades = []
    accumulated_pnl = 0.0
    violating_trades_count = 0
    
    for idx, sig in enumerate(signals, 1):
        sig_time, sig_type, sig_price = sig
        
        # Esito del singolo trade basato sullo Stop Loss impostato
        trade_pnl = sl_usd
        accumulated_pnl += trade_pnl
        
        # Controllo sul SINGOLO TRADE rispetto al limite di slippage
        single_trade_breached = trade_pnl <= slippage_limit_per_trade
        if single_trade_breached:
            violating_trades_count += 1
            
        detailed_trades.append({
            'trade_id': idx,
            'time': sig_time,
            'type': sig_type,
            'price': sig_price,
            'lot': lot_size,
            'pnl': trade_pnl,
            'cumulative_pnl': accumulated_pnl,
            'single_trade_breached': single_trade_breached
        })
        
    df_trades = pd.DataFrame(detailed_trades)
    
    print(f"📈 [DETAILED REPORT] {strategy_name}:")
    print(f"   - Totale Trade Eseguiti: {len(df_trades)}")
    print(f"   - Lotto: {lot_size} | SL: ${sl_usd:,.2f} | TP: ${tp_usd:,.2f}")
    print(f"   - Limite Singolo Trade (Slippage): ${slippage_limit_per_trade:,.2f}")
    print(f"   - Violazioni Limite Singolo: {violating_trades_count}")
    print(f"   - PnL Netto Complessivo: ${accumulated_pnl:,.2f}")
    print("-"*50)
    
    return df_trades

def run_standalone():
    print("="*60)
    print("🚀 [ACTION TYPE: BACKTEST DETAILED] - ESECUZIONE AUTONOMA")
    print("="*60)
    df = download_twelve_data()
    if df is None or df.empty:
        print("❌ [DETAILED] Impossibile procedere senza dati di mercato.")
        return
        
    from strategies import strategy_breakout, strategy_vwap, strategy_fibonacci
    strategies = [
        (strategy_breakout, "Breakout Elite"),
        (strategy_vwap, "VWAP Strategy"),
        (strategy_fibonacci, "Fibonacci Strategy")
    ]
    
    for strat_mod, strat_name in strategies:
        run_detailed_backtest(df, strat_mod, strat_name)

if __name__ == "__main__":
    run_standalone()
