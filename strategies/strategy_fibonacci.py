# ==========================================
# STRATEGIA FIBONACCI (M5) - BILANCIATA
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
    open_p = df['open'] if 'open' in df.columns else close

    window = 25  # Finestra leggermente più reattiva per guadagnare qualche segnale in più
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
        
        # Tolleranza leggermente ampliata allo 0.4% per generare qualche trade in più mantenendo il filtro EMA
        if abs(c_close - fib_618) <= (diff * 0.004):
            if c_close > c_ema and c_close > c_open:
                signals.append((current_time, "BUY", c_close))
            elif c_close < c_ema and c_close < c_open:
                signals.append((current_time, "SELL", c_close))

    return signals
