# ==========================================
# STRATEGIA BREAKOUT ELITE (M5) - BILANCIATA
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < 15:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    lookback = 8
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()
    vol_ma = volume.rolling(window=lookback).mean()

    for i in range(lookback, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_vol = volume.iloc[i]
        
        min_vol = vol_ma.iloc[i] * 0.9 if not pd.isna(vol_ma.iloc[i]) else 1.0
        
        if c_close > rolling_high.iloc[i - 1] and c_vol >= min_vol:
            signals.append((current_time, "BUY", c_close))
        elif c_close < rolling_low.iloc[i - 1] and c_vol >= min_vol:
            signals.append((current_time, "SELL", c_close))

    return signals
