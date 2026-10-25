import pandas as pd
import numpy as np

def run_adaptive_omnibus(df_candles, lot_size=1.04, sl_usd=2200.0, tp_usd=2000.0, slippage_limit=2800.0, verbose=True):
    """
    Motore Adattivo Omnibus - Fusione di Breakout Elite, VWAP e Fibonacci con ricalcolo giornaliero.
    """
    trades = []
    pip_value_per_lot = 10.0  
    
    price_sl_delta = sl_usd / (lot_size * pip_value_per_lot)
    price_tp_delta = tp_usd / (lot_size * pip_value_per_lot)

    if df_candles is None or df_candles.empty:
        return pd.DataFrame()

    df_candles = df_candles.copy()
    df_candles['close'] = pd.to_numeric(df_candles['close'], errors='coerce')
    df_candles['high'] = pd.to_numeric(df_candles['high'], errors='coerce')
    df_candles['low'] = pd.to_numeric(df_candles['low'], errors='coerce')
    df_candles['dt'] = pd.to_datetime(df_candles['time'], errors='coerce')
    df_candles['date'] = df_candles['dt'].dt.date

    df_candles['prev_day_volatility'] = df_candles.groupby('date')['close'].transform(lambda x: x.std()).shift(24)

    window = 20
    df_candles['sma'] = df_candles['close'].rolling(window=window).mean()
    df_candles['std'] = df_candles['close'].rolling(window=window).std()
    df_candles['upper'] = df_candles['sma'] + (2.2 * df_candles['std'])
    df_candles['lower'] = df_candles['sma'] - (2.2 * df_candles['std'])

    df_candles['signal'] = None

    for idx in range(max(window, 5), len(df_candles)):
        curr_close = df_candles.loc[idx, 'close']
        upper = df_candles.loc[idx, 'upper']
        lower = df_candles.loc[idx, 'lower']
        sma_val = df_candles.loc[idx, 'sma']
        std_val = df_candles.loc[idx, 'std']
        
        be_sig = 'BUY' if curr_close > upper else ('SELL' if curr_close < lower else None)
        vwap_sig = 'BUY' if curr_close > (sma_val + std_val * 1.5) else ('SELL' if curr_close < (sma_val - std_val * 1.5) else None)
        
        r_high = df_candles.loc[idx-5:idx-1, 'high'].max()
        r_low = df_candles.loc[idx-5:idx-1, 'low'].min()
        fib_high = r_low + (r_high - r_low) * 0.786
        fib_low = r_low + (r_high - r_low) * 0.214
        fib_sig = 'BUY' if curr_close > fib_high else ('SELL' if curr_close < fib_low else None)
        
        signals = [be_sig, vwap_sig, fib_sig]
        buy_count = signals.count('BUY')
        sell_count = signals.count('SELL')
        
        raw_sig = None
        if buy_count >= 2:
            raw_sig = 'BUY'
        elif sell_count >= 2:
            raw_sig = 'SELL'
            
        df_candles.loc[idx, 'signal'] = raw_sig

    for i in range(len(df_candles)):
        row = df_candles.iloc[i]
        trade_type = row.get('signal')
        
        if trade_type in ['BUY', 'SELL']:
            entry_price = row['close']
            entry_time = row['time']
            entry_dt = row['dt']
            
            if trade_type == 'BUY':
                target_sl = entry_price - price_sl_delta
                target_tp = entry_price + price_tp_delta
            else:
                target_sl = entry_price + price_sl_delta
                target_tp = entry_price - price_tp_delta
                
            trade_result = None
            pnl = 0.0
            single_breached = False
            
            for j in range(i + 1, len(df_candles)):
                future_candle = df_candles.iloc[j]
                high = future_candle['high']
                low = future_candle['low']
                close_price = future_candle['close']
                future_dt = future_candle['dt']
                
                is_same_day = (pd.notna(entry_dt) and pd.notna(future_dt) and entry_dt.date() == future_dt.date())
                is_cutoff = (pd.notna(future_dt) and (future_dt.hour > 21 or (future_dt.hour == 21 and future_dt.minute >= 45)))
                
                if is_same_day and is_cutoff:
                    trade_result = 'TIMEOUT_2145'
                    pnl = (close_price - entry_price) * lot_size * pip_value_per_lot if trade_type == 'BUY' else (entry_price - close_price) * lot_size * pip_value_per_lot
                    break

                if trade_type == 'BUY':
                    hit_sl = (low <= target_sl)
                    hit_tp = (high >= target_tp)
                else:
                    hit_sl = (high >= target_sl)
                    hit_tp = (low <= target_tp)
                
                if hit_sl:
                    trade_result = 'SL'
                    pnl = -sl_usd
                    if sl_usd >= slippage_limit:
                        single_breached = True
                    break
                elif hit_tp:
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
                'pnl ($)': round(pnl, 2),
                'single_trade_breached': single_breached
            })
            
    df_results = pd.DataFrame(trades)
    if verbose and not df_results.empty:
        print(f"\n📋 RISULTATI ADAPTIVE OMNIBUS:")
        print(df_results.to_string(index=False))
        
    return df_results
