# ==========================================
# STRATEGIA FIBONACCI (M5) - TARGET 3+/GIORNO
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < 30:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']

    window = 15  # Reattivo per identificare swing ravvicinati su M5
    rolling_max = high.rolling(window=window).max()
    rolling_min = low.rolling(window=window).min()

    for i in range(window, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        max_val = rolling_max.iloc[i]
        min_val = rolling_min.iloc[i]
        
        diff = max_val - min_val
        if diff == 0:
            continue
            
        fib_618 = max_val - (diff * 0.618)
        
        # Tolleranza calibrata allo 0.8% dell'ampiezza per generare 3+ segnali/giorno
        if abs(c_close - fib_618) <= (diff * 0.008):
            if c_close > close.iloc[i-1]:
                signals.append((current_time, "BUY", c_close))
            elif c_close < close.iloc[i-1]:
                signals.append((current_time, "SELL", c_close))

    return signals
