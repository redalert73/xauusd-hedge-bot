import pandas as pd
import numpy as np

def run_detailed_backtest(df_candles, strategy_name, lot_size=1.04, sl_usd=2200.0, tp_usd=2000.0, slippage_limit=2800.0, verbose=True):
    """
    Motore di Calcolo Dettagliato - Unified Volatility Stress Test + Chiusura Forzata ore 22:00.
    Gestisce i trade aperti imponendo la chiusura prima del rollover serale.
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
    
    # Conversione della colonna temporale per il controllo dell'ora (22:00)
    df_candles['dt'] = pd.to_datetime(df_candles['time'], errors='coerce')

    # Indicatori di Volatilità (Bande di Bollinger a 20 periodi, 2.2 Deviazioni Standard)
    window = 20
    std_dev = 2.2
    df_candles['sma'] = df_candles['close'].rolling(window=window).mean()
    df_candles['std'] = df_candles['close'].rolling(window=window).std()
    df_candles['upper_band'] = df_candles['sma'] + (df_dev := std_dev * df_candles['std'])
    df_candles['lower_band'] = df_candles['sma'] - df_dev

    if 'signal' not in df_candles.columns or df_candles['signal'].dropna().empty:
        df_candles['signal'] = None
        
        for idx in range(window, len(df_candles)):
            curr_close = df_candles.loc[idx, 'close']
            upper = df_candles.loc[idx, 'upper_band']
            lower = df_candles.loc[idx, 'lower_band']
            
            raw_sig = None
            
            if strategy_name == 'Breakout Elite':
                if curr_close > upper:
                    raw_sig = 'BUY'
                elif curr_close < lower:
                    raw_sig = 'SELL'
                    
            elif strategy_name == 'VWAP Strategy':
                sma_val = df_candles.loc[idx, 'sma']
                if curr_close > sma_val + (df_candles.loc[idx, 'std'] * 1.5):
                    raw_sig = 'BUY'
                elif curr_close < sma_val - (df_candles.loc[idx, 'std'] * 1.5):
                    raw_sig = 'SELL'
                    
            elif strategy_name == 'Fibonacci Strategy':
                recent_high = df_candles.loc[idx-5:idx-1, 'high'].max()
                recent_low = df_candles.loc[idx-5:idx-1, 'low'].min()
                fib_zone = recent_low + (recent_high - recent_low) * 0.786
                if curr_close > fib_zone:
                    raw_sig = 'BUY'
                elif curr_close < (recent_low + (recent_high - recent_low) * 0.214):
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
                
                # 🛑 Regola Chiusura Forzata: se arriviamo alle ore 22:00 o oltre nella stessa data
                is_same_day = (pd.notna(entry_dt) and pd.notna(future_dt) and entry_dt.date() == future_dt.date())
                is_cutoff_time = (pd.notna(future_dt) and future_dt.hour >= 22)
                
                if is_same_day and is_cutoff_time:
                    trade_result = 'TIMEOUT_22'
                    # Calcolo PnL basato sulla differenza di prezzo alla chiusura forzata
                    if trade_type == 'BUY':
                        pnl = (close_price - entry_price) * lot_size * pip_value_per_lot
                    else:
                        pnl = (entry_price - close_price) * lot_size * pip_value_per_lot
                    break

                if trade_type == 'BUY':
                    hit_sl = (low <= target_sl)
                    hit_tp = (high >= target_tp)
                else:
                    hit_sl = (high >= target_sl)
                    hit_tp = (low <= target_tp)
                
                # Priorità assoluta SL in caso di doppio tocco
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
        print(f"\n📋 ELENCO PUNTUALE TRADE (CUTOFF ORE 22) -> {strategy_name.upper()}:")
        print(df_results.to_string(index=False))
        
    return df_results
