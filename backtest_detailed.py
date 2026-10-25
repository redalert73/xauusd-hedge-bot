import pandas as pd
import numpy as np

def run_detailed_backtest(df_candles, strategy_name, lot_size=1.04, sl_usd=2400.0, tp_usd=2000.0, slippage_limit=2800.0, verbose=True):
    """
    Motore di Calcolo Dettagliato - Modalità Breakout Standard (Target SL).
    I segnali seguono la rottura per testare la cattura nei fakeout e massimizzare i test di Stop Loss.
    """
    trades = []
    pip_value_per_lot = 10.0  # Valore indicativo punto/pip per XAU/USD per lotto
    
    price_sl_delta = sl_usd / (lot_size * pip_value_per_lot)
    price_tp_delta = tp_usd / (lot_size * pip_value_per_lot)

    if df_candles is None or df_candles.empty:
        return pd.DataFrame()

    df_candles = df_candles.copy()

    # --- CALCOLO EMA 20, 30, 100 ---
    df_candles['close'] = pd.to_numeric(df_candles['close'], errors='coerce')
    df_candles['ema_20'] = df_candles['close'].ewm(span=20, adjust=False).mean()
    df_candles['ema_30'] = df_candles['close'].ewm(span=30, adjust=False).mean()
    df_candles['ema_100'] = df_candles['close'].ewm(span=100, adjust=False).mean()

    if 'signal' not in df_candles.columns or df_candles['signal'].dropna().empty:
        df_candles['signal'] = None
        
        for idx in range(100, len(df_candles)):
            prev_high = df_candles.loc[idx - 1, 'high']
            prev_low = df_candles.loc[idx - 1, 'low']
            curr_close = df_candles.loc[idx, 'close']
            
            e20 = df_candles.loc[idx, 'ema_20']
            e30 = df_candles.loc[idx, 'ema_30']
            e100 = df_candles.loc[idx, 'ema_100']
            
            raw_sig = None
            
            is_bullish_stack = (e20 > e30) and (e30 > e100)
            is_bearish_stack = (e20 < e30) and (e30 < e100)
            
            if strategy_name == 'Breakout Elite':
                # Segnale diretto nella direzione del breakout (senza inversione)
                if curr_close > prev_high and not is_bullish_stack:
                    raw_sig = 'BUY' 
                elif curr_close < prev_low and not is_bearish_stack:
                    raw_sig = 'SELL' 
                    
            elif strategy_name == 'VWAP Strategy':
                if curr_close > e20:
                    raw_sig = 'BUY'
                elif curr_close < e20:
                    raw_sig = 'SELL'
                    
            elif strategy_name == 'Fibonacci Strategy':
                mid_point = (prev_high + prev_low) / 2
                if curr_close > mid_point:
                    raw_sig = 'BUY'
                elif curr_close <= mid_point:
                    raw_sig = 'SELL'

            # Assegnazione diretta del segnale (Breakout Standard)
            df_candles.loc[idx, 'signal'] = raw_sig

    for i in range(len(df_candles)):
        row = df_candles.iloc[i]
        trade_type = row.get('signal')
        
        if trade_type in ['BUY', 'SELL']:
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
    
    if verbose and not df_results.empty:
        print(f"\n📋 ELENCO PUNTUALE TRADE (TARGET SL STRESS) -> {strategy_name.upper()}:")
        print(df_results.to_string(index=False))
        
    return df_results
