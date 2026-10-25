import pandas as pd

def run_detailed_backtest(df_candles, strategy_name, lot_size=1.04, sl_usd=2400.0, tp_usd=2000.0, slippage_limit=2800.0, verbose=True):
    """
    Motore di Calcolo Dettagliato - Modalità Stress-Test Avverso (Priorità Assoluta SL).
    Generazione segnali ultra-rapida (finestra = 1) per innescare i trade il prima possibile.
    """
    trades = []
    pip_value_per_lot = 10.0  # Valore indicativo punto/pip per XAU/USD per lotto
    
    price_sl_delta = sl_usd / (lot_size * pip_value_per_lot)
    price_tp_delta = tp_usd / (lot_size * pip_value_per_lot)

    if df_candles is None or df_candles.empty:
        return pd.DataFrame()

    df_candles = df_candles.copy()

    # Generazione segnali ultra-rapida (finestra = 1 per attivazione immediata)
    if 'signal' not in df_candles.columns or df_candles['signal'].dropna().empty:
        df_candles['signal'] = None
        
        # Dalla seconda candela in poi, confronta subito con la precedente
        for idx in range(1, len(df_candles)):
            prev_high = df_candles.loc[idx - 1, 'high']
            prev_low = df_candles.loc[idx - 1, 'low']
            curr_close = df_candles.loc[idx, 'close']
            
            if strategy_name == 'Breakout Elite':
                if curr_close > prev_high:
                    df_candles.loc[idx, 'signal'] = 'BUY'
                elif curr_close < prev_low:
                    df_candles.loc[idx, 'signal'] = 'SELL'
            elif strategy_name == 'VWAP Strategy':
                # Esempio reattivo immediato basato su soglia rapida
                curr_open = df_candles.loc[idx, 'open']
                if curr_close > curr_open:
                    df_candles.loc[idx, 'signal'] = 'BUY'
                else:
                    df_candles.loc[idx, 'signal'] = 'SELL'
            elif strategy_name == 'Fibonacci Strategy':
                # Trigger immediato basato sul range precedente
                mid_point = (prev_high + prev_low) / 2
                if curr_close > mid_point:
                    df_candles.loc[idx, 'signal'] = 'BUY'
                else:
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
            
            # Scorrimento con priorità assoluta e inderogabile sullo Stop Loss
            for j in range(i + 1, len(df_candles)):
                future_candle = df_candles.iloc[j]
                high = future_candle['high']
                low = future_candle['low']
                
                if trade_type == 'BUY':
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
    
    # Stampa i singoli trade solo se verbose è True
    if verbose and not df_results.empty:
        print(f"\n📋 ELENCO PUNTUALE SINGOLI TRADE (STRESS SL) -> {strategy_name.upper()}:")
        print(df_results.to_string(index=False))
        
    return df_results
