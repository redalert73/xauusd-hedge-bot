# ==========================================
# STRATEGIA FIBONACCI (M5) - ELITE PRECISION
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < 60:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    open_p = df['open'] if 'open' in df.columns else close

    window = 35
    rolling_max = high.rolling(window=window).max()
    rolling_min = low.rolling(window=window).min()
    ema50 = close.ewm(span=50, adjust=False).mean()

    for i in range(window, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_open = open_p.iloc[i]
        max_val = rolling_max.iloc[i]
        min_val = rolling_min.iloc[i]
        c_ema = ema50.iloc[i]
        
        diff = max_val - min_val
        if diff == 0:
            continue
            
        fib_618 = max_val - (diff * 0.618)
        
        # Tolleranza stretta e candela direzionale forte (corpo candela > 40% dell'escursione)
        body_size = abs(c_close - c_open)
        total_range = high.iloc[i] - low.iloc[i]
        
        if total_range > 0 and (body_size / total_range) >= 0.4:
            if abs(c_close - fib_618) <= (diff * 0.002):
                if c_close > c_ema and c_close > c_open:
                    signals.append((current_time, "BUY", c_close))
                elif c_close < c_ema and c_close < c_open:
                    signals.append((current_time, "SELL", c_close))

    return signals
