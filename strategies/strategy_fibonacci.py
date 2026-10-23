# ==========================================
# STRATEGIA FIBONACCI RETRACEMENT (M5 / M15)
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    """
    Strategia Fibonacci Retracement basata sui dati storici e configurazione centrale.
    """
    signals = []
    if df is None or len(df) < 50:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']

    window = 30
    rolling_max = high.rolling(window=window).max()
    rolling_min = low.rolling(window=window).min()

    for i in range(window, len(df)):
        # Utilizza direttamente l'indice datetime del DataFrame
        current_time = df.index[i]
        c_close = close.iloc[i]
        max_val = rolling_max.iloc[i]
        min_val = rolling_min.iloc[i]
        
        diff = max_val - min_val
        if diff == 0:
            continue
            
        fib_618 = max_val - (diff * 0.618)
        
        if abs(c_close - fib_618) < (diff * 0.01):
            if c_close > close.iloc[i-1]:
                signals.append((current_time, "BUY", c_close))
            else:
                signals.append((current_time, "SELL", c_close))

    return signals
