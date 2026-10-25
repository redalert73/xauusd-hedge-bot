import pandas as pd
import numpy as np

def run_adaptive_liquidity_sweep(df_candles, lot_size=1.04, sl_usd=2200.0, tp_usd=2000.0, slippage_limit=2800.0, verbose=True):
    """
    Motore Adattivo - Liquidity Sweep & Volatility Exhaustion (XAU/USD).
    Ricalcola i range giornalieri precedenti e forza l'esposizione allo Stop Loss.
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
    df_candles['open'] = pd.to_numeric(df_candles['open'], errors='coerce')
    df_candles['dt'] = pd.to_datetime(df_candles['time'], errors='coerce')
    df_candles['date'] = df_candles['dt'].dt.date

    # Adattività giornaliera: estrazione dinamica dei massimi/minimi del giorno precedente
    df_candles['daily_high_prev'] = df_candles.groupby('date')['high'].transform(lambda x: x.max()).shift(24)
    df_candles['daily_low_prev'] = df_candles.groupby('date')['low'].transform(lambda x: x.min()).shift(24)

    window = 20
    df_candles['sma'] = df_candles['close'].rolling(window=window).mean()
    df_candles['std'] = df_candles['close'].rolling(window=window).std()
    df_candles['upper'] = df_candles['sma'] + (2.2 * df_candles['std'])
    df_candles['lower'] = df_candles['sma'] - (2.2 * df_candles['std'])

    df_candles['signal'] = None

    for idx in range(max(window, 24), len(df_candles)):
        curr_close = df_candles.loc[idx, 'close']
        curr_high = df_candles.loc[idx, 'high']
        curr_low = df_candles.loc[idx, 'low']
        pdh = df_candles.loc[idx, 'daily_high_prev']
        pdl = df_candles.loc[idx, 'daily_low_prev']
        upper = df_candles.loc[idx, 'upper']
        lower = df_candles.loc[idx, 'lower']
        
        raw_sig = None
        if pd.notna(pdh) and pd.notna(pdl):
            if curr_high >= pdh and curr_close > upper:
                raw_sig = 'BUY'
            elif curr_low <= pdl and curr_close < lower:
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
                
                # Chiusura forzata rigorosa alle 21:45
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
        print(f"\n📋 RISULTATI ADAPTIVE LIQUIDITY SWEEP:")
        print(df_results.to_string(index=False))
        
    return df_results
