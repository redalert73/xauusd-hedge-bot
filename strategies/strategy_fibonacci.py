# ==========================================
# STRATEGIA FIBONACCI (M5) - ALTA PRECISIONE
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

    window = 30
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
        
        # Tolleranza stretta sul livello 0.618 (0.3% dell'ampiezza)
        if abs(c_close - fib_618) <= (diff * 0.003):
            # Conferma di rimbalzo in direzione del trend (EMA 50) e candela di forza
            if c_close > c_ema and c_close > c_open:  # Rimbalzo long con candela verde
                signals.append((current_time, "BUY", c_close))
            elif c_close < c_ema and c_close < c_open:  # Rimbalzo short con candela rossa
                signals.append((current_time, "SELL", c_close))

    return signals
