# ==========================================
# STRATEGIA BREAKOUT ELITE (M5) - TARGET 3+/GIORNO
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < config.ATR_PERIOD + 20:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    momentum = close.diff(config.ATR_PERIOD)
    lookback = 12  # Finestra ridotta per intercettare i breakout intraday M5
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()
    vol_ma = volume.rolling(window=lookback).mean()

    for i in range(lookback + 1, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_vol = volume.iloc[i]
        c_mom = momentum.iloc[i] if not np.isnan(momentum.iloc[i]) else 0.0
        
        # Filtro volume a 1.1x per garantire la frequenza di 3+ segnali/giorno
        min_vol_required = vol_ma.iloc[i] * 1.1
        
        if c_close > (rolling_high.iloc[i - 1] + config.PRICE_OFFSET) and c_vol >= min_vol_required and c_mom >= 0.1:
            signals.append((current_time, "BUY", c_close))
        elif c_close < (rolling_low.iloc[i - 1] - config.PRICE_OFFSET) and c_vol >= min_vol_required and c_mom <= -0.1:
            signals.append((current_time, "SELL", c_close))

    return signals
