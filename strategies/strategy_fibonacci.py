# ==========================================
# STRATEGIA FIBONACCI - TARGET: ESAURIMENTO (SL)
# ==========================================

import pandas as pd
import numpy as np

def run(df):
    signals = []
    if df is None or len(df) < 30:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    open_p = df['open'] if 'open' in df.columns else close

    window = 20
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
        
        # Entriamo al tocco del ritracciamento ma con candela di colore opposto (esaurimento imminente)
        if abs(c_close - fib_618) <= (diff * 0.002):
            if c_close < c_open:  # Tocca ma chiude rossa -> BUY debole destinato allo SL
                signals.append((current_time, "BUY", c_close))
            elif c_close > c_open: # Tocca ma chiude verde -> SELL debole destinato allo SL
                signals.append((current_time, "SELL", c_close))

    return signals
