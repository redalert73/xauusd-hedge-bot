# ==========================================
# STRATEGIA BREAKOUT ELITE (M5) - ATTIVA
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < config.ATR_PERIOD + 10:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    # Calcolo ATR per misurare la volatilità reale su M5
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=config.ATR_PERIOD).mean()
    
    lookback = 10
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()
    vol_ma = volume.rolling(window=lookback).mean()

    for i in range(max(lookback, config.ATR_PERIOD), len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_vol = volume.iloc[i]
        c_atr = atr.iloc[i]
        
        if pd.isna(c_atr) or c_atr == 0:
            continue
            
        # Breakout confermato se il prezzo supera il massimo precedente di almeno 0.3 * ATR
        if c_close > (rolling_high.iloc[i - 1] + (c_atr * 0.3)) and c_vol >= vol_ma.iloc[i]:
            signals.append((current_time, "BUY", c_close))
        elif c_close < (rolling_low.iloc[i - 1] - (c_atr * 0.3)) and c_vol >= vol_ma.iloc[i]:
            signals.append((current_time, "SELL", c_close))

    return signals
