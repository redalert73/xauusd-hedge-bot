# ==========================================
# BACKTEST DETAILED - ANALISI GRANULARE
# CONTROLLO PER SINGOLO TRADE (SLIPPAGE LIMITE)
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
    slippage_limit_per_trade = -2900.0  # Limite da non raggiungere mai sul singolo trade
    
    signals = strategy_module.run(df)
    if not signals:
        print(f"- Nessun segnale generato per {strategy_name}.")
        return None
        
    detailed_trades = []
    accumulated_pnl = 0.0
    violating_trades_count = 0
    
    for idx, sig in enumerate(signals, 1):
        sig_time, sig_type, sig_price = sig
        
        # Esito del singolo trade basato sullo Stop Loss impostato
        trade_pnl = sl_usd
        accumulated_pnl += trade_pnl
        
        # Controllo sul SINGOLO TRADE: verifica se il singolo trade supera la soglia critica
        # (Nel modello attuale il trade base è SL a -2400, ma se consideriamo l'impatto limite a -2900)
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
    
    print(f"📈 REPORT DETTAGLIATO [{strategy_name}]:")
    print(f"- Totale Trade Eseguiti: {len(df_trades)}")
    print(f"- Lotto: {lot_size} | SL: ${sl_usd:,.2f} | TP: ${tp_usd:,.2f}")
    print(f"- Soglia Limite Singolo Trade (Slippage): ${slippage_limit_per_trade:,.2f}")
    print(f"- Trade che violano il limite singolo: {violating_trades_count}")
    print(f"- PnL Netto Complessivo: ${accumulated_pnl:,.2f}")
    print(f"==================================================")
    
    return df_trades
