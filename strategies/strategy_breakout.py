# ==========================================
# STRATEGIA BREAKOUT ELITE (M5) - ALTA SELETTIVITÀ
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < config.ATR_PERIOD + 30:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    momentum = close.diff(config.ATR_PERIOD)
    lookback = 25
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()
    vol_ma = volume.rolling(window=lookback).mean()

    for i in range(lookback + 1, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_vol = volume.iloc[i]
        c_mom = momentum.iloc[i] if not np.isnan(momentum.iloc[i]) else 0.0
        
        # Filtri restrittivi: volume a 2.2x e momentum forte (> 0.8)
        min_vol_required = vol_ma.iloc[i] * 2.2
        
        if c_close > (rolling_high.iloc[i - 1] + config.PRICE_OFFSET) and c_vol >= min_vol_required and c_mom >= 0.8:
            signals.append((current_time, "BUY", c_close))
        elif c_close < (rolling_low.iloc[i - 1] - config.PRICE_OFFSET) and c_vol >= min_vol_required and c_mom <= -0.8:
            signals.append((current_time, "SELL", c_close))

    return signals
