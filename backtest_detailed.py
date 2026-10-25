import pandas as pd

def run_detailed_backtest(df_candles, strategy_name, lot_size=1.04, sl_usd=2400.0, tp_usd=2000.0, slippage_limit=2800.0):
    """
    Simulazione Backtest Dettagliata - Modalità Stress-Test Avverso (Priorità Assoluta SL).
    I trade vengono verificati dando precedenza inflessibile al raggiungimento dello Stop Loss (SL).
    """
    trades = []
    pip_value_per_lot = 10.0  # Valore indicativo punto/pip per XAU/USD per lotto
    
    # Calcolo delta prezzo in base ai valori in USD bloccati
    price_sl_delta = sl_usd / (lot_size * pip_value_per_lot)
    price_tp_delta = tp_usd / (lot_size * pip_value_per_lot)
    
    print(f"\n============================================================")
    print(f"📊 [ACTION TYPE: BACKTEST DETAILED] -> Analisi: {strategy_name.upper()}")
    print(f"============================================================")

    if df_candles is None or df_candles.empty:
        print(f"⚠️ [DETAILED] Nessun dato disponibile o candele vuote per {strategy_name}.")
        return pd.DataFrame()

    df_candles = df_candles.copy()

    # Generazione automatica dei segnali se assenti nella struttura
    if 'signal' not in df_candles.columns or df_candles['signal'].dropna().empty:
        print(f"💡 [SIGNAL GENERATOR] Generazione automatica segnali di breakout per {strategy_name}...")
        df_candles['signal'] = None
        
        window = 10
        df_candles['rolling_max'] = df_candles['high'].shift(1).rolling(window=window).max()
        df_candles['rolling_min'] = df_candles['low'].shift(1).rolling(window=window).min()
        
        for idx in range(window, len(df_candles)):
            if df_candles.loc[idx, 'close'] > df_candles.loc[idx, 'rolling_max']:
                df_candles.loc[idx, 'signal'] = 'BUY'
            elif df_candles.loc[idx, 'close'] < df_candles.loc[idx, 'rolling_min']:
                df_candles.loc[idx, 'signal'] = 'SELL'

    for i in range(len(df_candles)):
        row = df_candles.iloc[i]
        
        if row.get('signal') in ['BUY', 'SELL']:
            trade_type = row['signal']
            entry_price = row['close']
            entry_time = row['time']
            
            if trade_type == 'BUY':
                target_sl = entry_price - price_sl_delta
                target_tp = entry_price + price_tp_delta
            else: # SELL
                target_sl = entry_price + price_sl_delta
                target_tp = entry_price - price_tp_delta
                
            trade_result = None
            pnl = 0.0
            single_breached = False
            
            # Scorrimento candele successive con priorità assoluta e inderogabile sullo Stop Loss
            for j in range(i + 1, len(df_candles)):
                future_candle = df_candles.iloc[j]
                high = future_candle['high']
                low = future_candle['low']
                
                if trade_type == 'BUY':
                    # STRESS-TEST AVVERSO: Controllo RIGOROSO e PRIORITARIO dello Stop Loss (Minimo)
                    if low <= target_sl:
                        trade_result = 'SL'
                        pnl = -sl_usd
                        if sl_usd >= slippage_limit:
                            single_breached = True
                        break
                    elif high >= target_tp:
                        trade_result = 'TP'
                        pnl = tp_usd
                        break
                elif trade_type == 'SELL':
                    # STRESS-TEST AVVERSO: Controllo RIGOROSO e PRIORITARIO dello Stop Loss (Massimo)
                    if high >= target_sl:
                        trade_result = 'SL'
                        pnl = -sl_usd
                        if sl_usd >= slippage_limit:
                            single_breached = True
                        break
                    elif low <= target_tp:
                        trade_result = 'TP'
                        pnl = tp_usd
                        break
            
            if trade_result is None:
                trade_result = 'OPEN'
                pnl = 0.0

            trades.append({
                'trade_id': len(trades) + 1,
                'time': entry_time,
                'type': trade_type,
                'price': entry_price,
                'result': trade_result,
                'pnl ($)': pnl,
                'single_trade_breached': single_breached
            })
            
    df_results = pd.DataFrame(trades)
    
    if not df_results.empty:
        print("\n📋 ELENCO PUNTUALE SINGOLI TRADE (STRESS SL ABSOLUTE PRIORITY):")
        print(df_results.to_string(index=False))
        
        tp_wins = len(df_results[df_results['result'] == 'TP'])
        sl_losses = len(df_results[df_results['result'] == 'SL'])
        net_pnl = df_results['pnl ($)'].sum()
        violations = len(df_results[df_results['single_trade_breached'] == True])
        
        print("\n------------------------------------------------------------")
        print(f"📈 [DETAILED REPORT SUMMARY] -> {strategy_name.upper()}:")
        print(f"- Totale Trade Eseguiti: {len(df_results)}")
        print(f"- 🎯 Totale Trade in Take Profit (TP): {tp_wins}")
        print(f"- ❌ Totale Trade in Stop Loss (SL - Stress Avverso): {sl_losses}")
        print(f"- Lotto: {lot_size} | SL: ${-sl_usd:,.2f} | TP: ${tp_usd:,.2f}")
        print(f"- Limite Singolo Trade (Slippage): ${-slippage_limit:,.2f}")
        print(f"- Violazioni Limite Singolo: {violations}")
        print(f"- PnL Netto Complessivo: ${net_pnl:,.2f}")
        print("============================================================\n")
    else:
        print(f"⚠️ [DETAILED] Nessun trade generato per {strategy_name}.")
        
    return df_results
