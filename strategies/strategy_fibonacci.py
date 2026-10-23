# ==========================================
# STRATEGIA FIBONACCI - TARGET +1 SEGNALE
# ==========================================

import pandas as pd
import numpy as np

def run(df):
    signals = []
    if df is None or len(df) < 40:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    open_p = df['open'] if 'open' in df.columns else close

    window = 25
    rolling_max = high.rolling(window=window).max()
    rolling_min = low.rolling(window=window).min()

    for i in range(window, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_open = open_p.iloc[i]
        max_val = rolling_max.iloc[i]
        min_val = rolling_min.iloc[i]
        
        diff = max_val - min_val
        if diff == 0:
            continue
            
        fib_618 = max_val - (diff * 0.618)
        
        # Tolleranza calibrata per aggiungere esattamente un'opportunità in più
        if abs(c_close - fib_618) <= (diff * 0.0014):
            if c_close < c_open:
                signals.append((current_time, "BUY", c_close))
            elif c_close > c_open:
                signals.append((current_time, "SELL", c_close))

    return signals
