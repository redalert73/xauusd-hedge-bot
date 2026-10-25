import os
import requests
import pandas as pd
from backtest_detailed import run_detailed_backtest

def load_market_data():
    api_key = os.getenv('TWELVE_DATA_API_KEY', 'demo')
    symbol = 'XAU/USD'
    interval = '1h'
    outputsize = 500
    
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={api_key}"
    
    try:
        print(f"🌐 [TWELVE DATA] Connessione in corso per il download di {symbol}...")
        response = requests.get(url)
        data = response.json()
        
        if data.get("status") == "ok" and "values" in data:
            df = pd.DataFrame(data["values"])
            df = df.rename(columns={'datetime': 'time'})
            
            numeric_cols = ['open', 'high', 'low', 'close']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            df = df.sort_values('time').reset_index(drop=True)
            
            if 'signal' not in df.columns:
                df['signal'] = None
            
            print(f"✅ Dati scaricati con successo da Twelve Data: {len(df)} candele elaborate.")
            return df
        else:
            print(f"⚠️ Errore API Twelve Data: {data.get('message', 'Risposta non valida')}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"⚠️ Errore di connessione a Twelve Data API: {e}")
        return pd.DataFrame()

def main():
    print("============================================================")
    print("🚀 [ACTION TYPE: BACKTEST MASTER] - AVVIO COORDINATORE (STRESS SL)")
    print("============================================================")
    print("🔹 Parametri Operativi Bloccati:")
    print("- Lotto: 1.04")
    print("- Stop Loss (SL): -$2,400.0 USD")
    print("- Take Profit (TP): $2,000.0 USD")
    print("- Limite Singolo Trade (Slippage): -$2,800.0 USD")
    print("- Modalità: Stress-Test Avverso (Priorità SL / Master Sintetico)")
    print("============================================================\n")

    df_candles = load_market_data()
    
    if df_candles.empty:
        print("❌ Errore critico: Impossibile recuperare i dati da Twelve Data.")
        return

    strategies = ['Breakout Elite', 'VWAP Strategy', 'Fibonacci Strategy']
    summary_data = []

    for strat in strategies:
        print(f"⚙️ [MASTER] Elaborazione strategia: {strat}")
        df_results = run_detailed_backtest(df_candles, strat)
        
        if not df_results.empty:
            total_trades = len(df_results)
            tp_wins = len(df_results[df_results['result'] == 'TP'])
            sl_losses = len(df_results[df_results['result'] == 'SL'])
            net_pnl = df_results['pnl ($)'].sum()
            violations = len(df_results[df_results['single_trade_breached'] == True])
        else:
            total_trades = 0
            tp_wins = 0
            sl_losses = 0
            net_pnl = 0.0
            violations = 0

        summary_data.append({
            'Strategy': strat,
            'Total Trades': total_trades,
            'SL Losses': sl_losses,
            'TP Wins': tp_wins,
            'Net PnL ($)': net_pnl,
            'Violations': violations
        })

    print("\n============================================================")
    print("📋 [ACTION REPORT] RIEPILOGO COMPLESSIVO - STRESS TEST SL")
    print("============================================================")
    df_summary = pd.DataFrame(summary_data)
    print(df_summary.to_string(index=False))
    print("============================================================")

if __name__ == '__main__':
    main()
