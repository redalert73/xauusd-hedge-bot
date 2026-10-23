# ==========================================
# STRATEGIA BREAKOUT ELITE (M5) - SBLOCCATA
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < 20:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    # Finestra di breakout a 10 periodi su M5 per maggiore reattività
    lookback = 10
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()
    vol_ma = volume.rolling(window=lookback).mean()

    for i in range(lookback, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_vol = volume.iloc[i]
        
        # Sogliamo leggermente il filtro sul volume (1.05x la media) ed eliminiamo offset rigidi troppo alti
        min_vol_required = vol_ma.iloc[i] * 1.05
        
        if c_close > rolling_high.iloc[i - 1] and c_vol >= min_vol_required:
            signals.append((current_time, "BUY", c_close))
        elif c_close < rolling_low.iloc[i - 1] and c_vol >= min_vol_required:
            signals.append((current_time, "SELL", c_close))

    return signals
