# ==========================================
# STRATEGIA BREAKOUT - FREQUENZA INTRA-DAY (6-8 TOT/GIORNO)
# ==========================================

import pandas as pd
import numpy as np

def run(df):
    signals = []
    if df is None or len(df) < 15:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']

    lookback = 8  
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()

    for i in range(lookback, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        prev_high = rolling_high.iloc[i - 1]
        prev_low = rolling_low.iloc[i - 1]

        if high.iloc[i] > prev_high and c_close < prev_high:
            signals.append((current_time, "BUY", c_close))
        elif low.iloc[i] < prev_low and c_close > prev_low:
            signals.append((current_time, "SELL", c_close))

    return signals
