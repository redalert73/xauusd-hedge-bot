# ==========================================
# BACKTEST MASTER - COORDINATORE GLOBALE
# CON SOGLIA CRITICA DI SLIPPAGE
# ==========================================

import pandas as pd
import requests
from backtest_detailed import run_detailed_backtest

def download_twelve_data():
    import os
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("❌ ERRORE: TWELVE_DATA_API_KEY non trovata.")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=500&apikey={api_key}&timezone=UTC"
    response = requests.get(url)
    data = response.json()
    
    if "values" not in data:
        print("❌ ERRORE nel recupero dati da Twelve Data.")
        return None
        
    df = pd.DataFrame(data["values"])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def run_master():
    print("==================================================")
    print("🚀 AVVIO BACKTEST MASTER - XAU/USD (5min)")
    print("==================================================")
    print("🔹 Parametri Operativi Bloccati:")
    print("   - Lotto: 1.04")
    print("   - Stop Loss (SL): -$2,400.0 USD")
    print("   - Take Profit (TP): $2,000.0 USD")
    print("   - Soglia Critica (Slippage): -$2,900.0 USD (Da non raggiungere mai)")
    print("==================================================")
    
    df = download_twelve_data()
    if df is None or df.empty:
        print("❌ Impossibile procedere senza dati di mercato.")
        return
        
    from strategies import strategy_breakout, strategy_vwap, strategy_fibonacci
    
    strategies = [
        (strategy_breakout, "Breakout Elite"),
        (strategy_vwap, "VWAP Strategy"),
        (strategy_fibonacci, "Fibonacci Strategy")
    ]
    
    master_summary = []
    
    for strat_mod, strat_name in strategies:
        df_trades = run_detailed_backtest(df, strat_mod, strat_name)
        if df_trades is not None and not df_trades.empty:
            total_trades = len(df_trades)
            net_pnl = df_trades['cumulative_pnl'].iloc[-1]
            max_dd = df_trades['cumulative_pnl'].min()
            breached = df_trades['threshold_breached'].any()
            
            master_summary.append({
                'Strategy': strat_name,
                'Total Trades': total_trades,
                'Net PnL ($)': net_pnl,
                'Max Drawdown ($)': max_dd,
                'Threshold Breached': breached
            })
            
    if master_summary:
        df_summary = pd.DataFrame(master_summary)
        print("\n==================================================")
        print("📋 RIEPILOGO COMPLESSIVO MASTER BACKTEST")
        print("==================================================")
        print(df_summary.to_string(index=False))
        print("==================================================")

if __name__ == "__main__":
    run_master()
