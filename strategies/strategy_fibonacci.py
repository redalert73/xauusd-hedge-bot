# ==========================================
# STRATEGIA FIBONACCI (M5) - ALTA SELETTIVITÀ
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < 50:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']

    window = 40
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
        
        # Tolleranza ridotta allo 0.3% e conferma di continuazione a 2 barre
        if abs(c_close - fib_618) < (diff * 0.003):
            if c_close > close.iloc[i-1] and close.iloc[i-1] > close.iloc[i-2]:
                signals.append((current_time, "BUY", c_close))
            elif c_close < close.iloc[i-1] and close.iloc[i-1] < close.iloc[i-2]:
                signals.append((current_time, "SELL", c_close))

    return signals
