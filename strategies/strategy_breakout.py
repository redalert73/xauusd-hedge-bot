# ==========================================
# STRATEGIA BREAKOUT - TARGET: FALSE ROTTURE (SL)
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

    lookback = 10
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()

    for i in range(lookback, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        prev_high = rolling_high.iloc[i - 1]
        prev_low = rolling_low.iloc[i - 1]

        # Falsa rottura rialzista (Fakeout): il prezzo supera il massimo ma chiude sotto -> Segnale BUY che prende lo SL al ribasso
        if high.iloc[i] > prev_high and c_close < prev_high:
            signals.append((current_time, "BUY", c_close))
        # Falsa rottura ribassista: il prezzo rompe il minimo ma chiude sopra -> Segnale SELL che prende lo SL al rialzo
        elif low.iloc[i] < prev_low and c_close > prev_low:
            signals.append((current_time, "SELL", c_close))

    return signals
