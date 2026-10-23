# ==========================================
# STRATEGIA BREAKOUT - RIDUZIONE SEGNALI (ALTA QUALITÀ)
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
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)
    vol_ma = volume.rolling(window=20).mean()

    lookback = 20  # Aumentato per filtrare i micro-breakout
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()

    for i in range(lookback, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        prev_high = rolling_high.iloc[i - 1]
        prev_low = rolling_low.iloc[i - 1]
        c_vol = volume.iloc[i]
        avg_vol = vol_ma.iloc[i]

        if pd.isna(avg_vol):
            continue

        # Richiediamo volumi alti sulla falsa rottura per evitare falsi segnali casuali
        if c_vol >= (avg_vol * 1.3):
            # Falsa rottura rialzista (Fakeout forte)
            if high.iloc[i] > prev_high and c_close < prev_high:
                signals.append((current_time, "BUY", c_close))
            # Falsa rottura ribassista (Fakeout forte)
            elif low.iloc[i] < prev_low and c_close > prev_low:
                signals.append((current_time, "SELL", c_close))

    return signals
