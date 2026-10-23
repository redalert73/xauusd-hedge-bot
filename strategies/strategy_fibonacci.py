# ==========================================
# STRATEGIA FIBONACCI - MAGGIORE SELETTIVITÀ
# ==========================================

import pandas as pd
import numpy as np

def run(df):
    signals = []
    if df is None or len(df) < 60:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    open_p = df['open'] if 'open' in df.columns else close
    ema50 = close.ewm(span=50, adjust=False).mean()

    window = 40  # Finestra più ampia per livelli più significativi
    rolling_max = high.rolling(window=window).max()
    rolling_min = low.rolling(window=window).min()

    for i in range(window, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_open = open_p.iloc[i]
        max_val = rolling_max.iloc[i]
        min_val = rolling_min.iloc[i]
        c_ema = ema50.iloc[i]
        
        diff = max_val - min_val
        if diff == 0 or pd.isna(c_ema):
            continue
            
        fib_618 = max_val - (diff * 0.618)
        
        # Tolleranza millimetrica e allineamento con il trend di medio periodo (EMA 50)
        if abs(c_close - fib_618) <= (diff * 0.0008):
            # Se siamo sotto la EMA cerchiamo rejection short, se sopra cerchiamo long
            if c_close < c_open and c_close < c_ema:
                signals.append((current_time, "BUY", c_close))
            elif c_close > c_open and c_close > c_ema:
                signals.append((current_time, "SELL", c_close))

    return signals
