# ==========================================
# BACKTEST DETAILED - ANALISI GRANULARE
# CON SOGLIA CRITICA DI SLIPPAGE
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
    slippage_threshold = -2900.0  # Soglia critica di passivo da non raggiungere mai
    
    signals = strategy_module.run(df)
    if not signals:
        print(f"- Nessun segnale generato per {strategy_name}.")
        return None
        
    detailed_trades = []
    accumulated_pnl = 0.0
    peak_pnl = 0.0
    max_drawdown = 0.0
    threshold_breached = False
    
    for idx, sig in enumerate(signals, 1):
        sig_time, sig_type, sig_price = sig
        
        # Ciascun trade genera l'esito di Stop Loss impostato
        trade_pnl = sl_usd
        accumulated_pnl += trade_pnl
        
        # Tracciamento del drawdown e controllo della soglia critica (Slippage)
        if accumulated_pnl < peak_pnl:
            current_dd = accumulated_pnl - peak_pnl
            if current_dd < max_drawdown:
                max_drawdown = current_dd
        else:
            peak_pnl = accumulated_pnl
            
        # Verifica se la soglia critica è stata violata
        if accumulated_pnl <= slippage_threshold:
            threshold_breached = True
            
        detailed_trades.append({
            'trade_id': idx,
            'time': sig_time,
            'type': sig_type,
            'price': sig_price,
            'lot': lot_size,
            'pnl': trade_pnl,
            'cumulative_pnl': accumulated_pnl,
            'threshold_breached': threshold_breached
        })
        
    df_trades = pd.DataFrame(detailed_trades)
    
    print(f"📈 REPORT DETTAGLIATO [{strategy_name}]:")
    print(f"- Totale Trade Eseguiti: {len(df_trades)}")
    print(f"- Lotto: {lot_size} | SL: ${sl_usd:,.2f} | TP: ${tp_usd:,.2f}")
    print(f"- Soglia Critica (Slippage): ${slippage_threshold:,.2f}")
    print(f"- PnL Netto Complessivo: ${accumulated_pnl:,.2f}")
    print(f"- Max Drawdown Raggiunto: ${max_drawdown:,.2f}")
    print(f"- Soglia Critica Violata: {'⚠️ SI' : 'NO' if not threshold_breached else '⚠️ SI'}")
    print(f"==================================================")
    
    return df_trades
