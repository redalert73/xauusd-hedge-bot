import pandas as pd
import numpy as np

def run_detailed_backtest(df_candles, strategy_name, lot_size=1.04, sl_usd=2400.0, tp_usd=2000.0, slippage_limit=2800.0, verbose=True):
    """
    Motore di Calcolo Dettagliato - Pure Raw Fade (Inversione Totale del Breakout Grezzo) + Strict SL Priority.
    Inverte i segnali di breakout per scommettere contro la rottura, massimizzando l'impatto degli Stop Loss.
    """
    trades = []
    pip_value_per_lot = 10.0  
    
    price_sl_delta = sl_usd / (lot_size * pip_value_per_lot)
    price_tp_delta = tp_usd / (lot_size * pip_value_per_lot)

    if df_candles is None or df_candles.empty:
        return pd.DataFrame()

    df_candles = df_candles.copy()
    df_candles['close'] = pd.to_numeric(df_candles['close'], errors='coerce')

    if 'signal' not in df_candles.columns or df_candles['signal'].dropna().empty:
        df_candles['signal'] = None
        
        for idx in range(50, len(df_candles)):
            prev_high = df_candles.loc[idx - 1, 'high']
            prev_low = df_candles.loc[idx - 1, 'low']
            curr_close = df_candles.loc[idx, 'close']
            curr_open = df_candles.loc[idx, 'open']
            
            raw_sig = None
            
            # 1. Calcolo del Breakout Grezzo di base
            if strategy_name == 'Breakout Elite':
                if curr_close > prev_high:
                    raw_sig = 'BUY'
                elif curr_close < prev_low:
                    raw_sig = 'SELL'
                    
            elif strategy_name == 'VWAP Strategy':
                if curr_close > curr_open + (curr_open * 0.001):
                    raw_sig = 'BUY'
                elif curr_close < curr_open - (curr_open * 0.001):
                    raw_sig = 'SELL'
                    
            elif strategy_name == 'Fibonacci Strategy':
                mid_point = (prev_high + prev_low) / 2
                if curr_close > mid_point:
                    raw_sig = 'BUY'
                elif curr_close <= mid_point:
                    raw_sig = 'SELL'

            # 🔄 2. INVERSIONE TOTALE (PURE RAW FADE): Entriamo esattamente all'opposto
            if raw_sig == 'BUY':
                df_candles.loc[idx, 'signal'] = 'SELL'
            elif raw_sig == 'SELL':
                df_candles.loc[idx, 'signal'] = 'BUY'

    for i in range(len(df_candles)):
        row = df_candles.iloc[i]
        trade_type = row.get('signal')
        
        if trade_type in ['BUY', 'SELL']:
            entry_price = row['close']
            entry_time = row['time']
            
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
                'pnl ($)': pnl,
                'single_trade_breached': single_breached
            })
            
    df_results = pd.DataFrame(trades)
    
    if verbose and not df_results.empty:
        print(f"\n📋 ELENCO PUNTUALE TRADE (PURE RAW FADE) -> {strategy_name.upper()}:")
        print(df_results.to_string(index=False))
        
    return df_results
