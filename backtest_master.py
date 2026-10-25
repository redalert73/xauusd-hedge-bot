# ==========================================
# 🟢 [BACKTEST MASTER] - COORDINATORE GLOBALE
# ==========================================

import pandas as pd
import requests
from backtest_detailed import run_detailed_backtest

def download_twelve_data():
    import os
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("❌ [MASTER] ERRORE: TWELVE_DATA_API_KEY non trovata.")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=500&apikey={api_key}&timezone=UTC"
    response = requests.get(url)
    data = response.json()
    
    if "values" not in data:
        print("❌ [MASTER] ERRORE nel recupero dati da Twelve Data.")
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
    print("\n" + "="*60)
    print("🚀 [ACTION TYPE: BACKTEST MASTER] - AVVIO COORDINATORE")
    print("="*60)
    print("🔹 Parametri Operativi Bloccati:")
    print("   - Lotto: 1.04")
    print("   - Stop Loss (SL): -$2,400.0 USD")
    print("   - Take Profit (TP): $2,000.0 USD")
    print("   - Limite Singolo Trade (Slippage): -$2,800.0 USD (Aggiornato)")
    print("   - Modalità: Stress-Test Avverso (Priorità SL)")
    print("="*60)
    
    df = download_twelve_data()
    if df is None or df.empty:
        print("❌ [MASTER] Impossibile procedere senza dati di mercato.")
        return
        
    from strategies import strategy_breakout, strategy_vwap, strategy_fibonacci
    
    strategies = [
        (strategy_breakout, "Breakout Elite"),
        (strategy_vwap, "VWAP Strategy"),
        (strategy_fibonacci, "Fibonacci Strategy")
    ]
    
    master_summary = []
    
    for strat_mod, strat_name in strategies:
        print(f"\n⚙️ [MASTER] Richiesta analisi dettagliata per: {strat_name}")
        df_trades = run_detailed_backtest(df, strat_mod, strat_name)
        
        if df_trades is not None and not df_trades.empty:
            total_trades = len(df_trades)
            net_pnl = df_trades['cumulative_pnl ($)'].iloc[-1]
            
            tp_wins = int((df_trades['result'] == 'WIN (TP)').sum())
            sl_losses = int(df_trades['result'].str.contains('LOSS').sum())
            violations = int(df_trades['single_trade_breached'].sum())
            
            master_summary.append({
                'Strategy': strat_name,
                'Total Trades': total_trades,
                'TP Wins': tp_wins,
                'SL Losses': sl_losses,
                'Net PnL ($)': net_pnl,
                'Single Trade Violations': violations
            })
            
    if master_summary:
        df_summary = pd.DataFrame(master_summary)
        print("\n" + "="*60)
        print("📋 [ACTION REPORT] RIEPILOGO COMPLESSIVO - BACKTEST MASTER")
        print("="*60)
        print(df_summary.to_string(index=False))
        print("="*60)

if __name__ == "__main__":
    run_master()
