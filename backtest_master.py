import sys
import argparse
import pandas as pd
import numpy as np
from backtest_liquidity_sweep_adaptive import run_adaptive_liquidity_sweep
from backtest_omnibus_adaptive import run_adaptive_omnibus

def fetch_market_data():
    np.random.seed(42)
    date_rng = pd.date_range(start='2026-01-01', periods=200, freq='h')
    base_price = 2300.0 + np.cumsum(np.random.randn(200) * 3.5)
    
    df = pd.DataFrame({
        'time': date_rng,
        'open': base_price + np.random.randn(200),
        'high': base_price + abs(np.random.randn(200) * 5),
        'low': base_price - abs(np.random.randn(200) * 5),
        'close': base_price + np.random.randn(200)
    })
    return df

def print_summary(strategy_name, df_results):
    print(f"\n==============================================================")
    print(f"📊 RIEPILOGO FINALE: {strategy_name.upper()}")
    print(f"==============================================================")
    if df_results.empty:
        print("Nessun trade registrato.")
        return

    total_trades = len(df_results)
    tp_count = len(df_results[df_results['result'] == 'TP'])
    sl_count = len(df_results[df_results['result'] == 'SL'])
    timeout_count = len(df_results[df_results['result'].str.contains('TIMEOUT', na=False)])
    open_count = len(df_results[df_results['result'] == 'OPEN'])
    
    breached_count = len(df_results[df_results['single_trade_breached'] == True]) if 'single_trade_breached' in df_results.columns else 0
    total_pnl = df_results['PnL ($)'].sum()

    print(f"• Totale Trade Eseguiti : {total_trades}")
    print(f"• Take Profit (TP)      : {tp_count}")
    print(f"• Stop Loss (SL)        : {sl_count}")
    print(f"• Chiusure a Orario     : {timeout_count}")
    print(f"• Ancora Aperti (OPEN)  : {open_count}")
    print(f"• Allarmi Slippage (>lim): {breached_count}")
    print(f"• PnL Totale Complessivo: ${total_pnl:,.2f}")
    print(f"==============================================================\n")

def main():
    parser = argparse.ArgumentParser(description="XAU/USD Adaptive Stress Test Master")
    parser.add_argument('--strategy', type=str, default='all', choices=['all', 'liquidity_sweep', 'omnibus'],
                        help="Seleziona quale strategia eseguire ('liquidity_sweep', 'omnibus' o 'all')")
    args = parser.parse_args()

    df_candles = fetch_market_data()
    
    if args.strategy in ['all', 'liquidity_sweep']:
        print("\n--------------------------------------------------")
        print("🔹 Esecuzione Strategia: Adaptive Liquidity Sweep")
        print("--------------------------------------------------")
        results_sweep = run_adaptive_liquidity_sweep(
            df_candles=df_candles, lot_size=1.04, sl_usd=2200.0, tp_usd=2000.0, slippage_limit=2800.0, verbose=True
        )
        print_summary("Adaptive Liquidity Sweep", results_sweep)

    if args.strategy in ['all', 'omnibus']:
        print("\n--------------------------------------------------")
        print("🔹 Esecuzione Strategia: Adaptive Omnibus")
        print("--------------------------------------------------")
        results_omnibus = run_adaptive_omnibus(
            df_candles=df_candles, lot_size=1.04, sl_usd=2200.0, tp_usd=2000.0, slippage_limit=2800.0, verbose=True
        )
        print_summary("Adaptive Omnibus", results_omnibus)
        
    print("✅ Esecuzione completata con successo.")

if __name__ == "__main__":
    main()
