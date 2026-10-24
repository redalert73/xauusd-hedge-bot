# ==========================================
# BACKTEST DETAILED - ANALISI GRANULARE
# CON PARAMETRI DEFINITIVI
# ==========================================

import pandas as pd
import numpy as np

def run_detailed_backtest(df, strategy_module, strategy_name):
    print(f"\n==================================================")
    print(f"📊 ESECUZIONE BACKTEST DETAILED: {strategy_name.upper()}")
    print(f"==================================================")
    
    # Parametri definitivi bloccati
    lot_size = 1.04
    sl_usd = -2400.0
    tp_usd = 2000.0
    slippage_usd = 2900.0
    
    signals = strategy_module.run(df)
    if not signals:
        print(f"- Nessun segnale generato per {strategy_name}.")
        return None
        
    detailed_trades = []
    accumulated_pnl = 0.0
    peak_pnl = 0.0
    max_drawdown = 0.0
    
    for idx, sig in enumerate(signals, 1):
        sig_time, sig_type, sig_price = sig
        
        # Calcolo dell'esito del trade combinando i paletti stabiliti
        # Ogni trade sconta l'impatto avverso dello SL corretto dallo slippage
        trade_pnl = sl_usd - slippage_usd
        accumulated_pnl += trade_pnl
        
        # Tracciamento dinamico del drawdown
        if accumulated_pnl < peak_pnl:
            current_dd = accumulated_pnl - peak_pnl
            if current_dd < max_drawdown:
                max_drawdown = current_dd
        else:
            peak_pnl = accumulated_pnl
            
        detailed_trades.append({
            'trade_id': idx,
            'time': sig_time,
            'type': sig_type,
            'price': sig_price,
            'lot': lot_size,
            'pnl': trade_pnl,
            'cumulative_pnl': accumulated_pnl
        })
        
    df_trades = pd.DataFrame(detailed_trades)
    
    print(f"📈 REPORT DETTAGLIATO [{strategy_name}]:")
    print(f"- Totale Trade Eseguiti: {len(df_trades)}")
    print(f"- Lotto: {lot_size} | SL: ${sl_usd:,.2f} | TP: ${tp_usd:,.2f} | Slippage: ${slippage_usd:,.2f}")
    print(f"- PnL Netto Complessivo: ${accumulated_pnl:,.2f}")
    print(f"- Max Drawdown Raggiunto: ${max_drawdown:,.2f}")
    print(f"==================================================")
    
    return df_trades

# Esecuzione dettagliata per tutte le strategie
def master_detailed_execution(df):
    from strategies import strategy_breakout, strategy_vwap, strategy_fibonacci
    
    print("BACKTEST DETAILED MASTER - CONFIGURAZIONE DEFINITIVA")
    print("==================================================")
    
    strategies = [
        (strategy_breakout, "Breakout Elite"),
        (strategy_vwap, "VWAP Strategy"),
        (strategy_fibonacci, "Fibonacci Strategy")
    ]
    
    all_reports = {}
    for strat_mod, strat_name in strategies:
        df_res = run_detailed_backtest(df, strat_mod, strat_name)
        if df_res is not None:
            all_reports[strat_name] = df_res
            
    print("\n✅ BACKTEST DETAILED COMPLETATO PER TUTTE LE STRATEGIE")
    return all_reports
