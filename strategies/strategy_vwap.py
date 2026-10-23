# ==========================================
# STRATEGIA VWAP (M5) - ALTA SELETTIVITÀ
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < 30:
        return signals

    if not isinstance(df.index, pd.DatetimeIndex):
        return signals

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    typical_price = (high + low + close) / 3
    df_temp = pd.DataFrame({
        'tp_vol': typical_price * volume,
        'vol': volume,
        'date': df.index.date
    })
    
    cum_tp_vol = df_temp.groupby('date')['tp_vol'].cumsum()
    cum_vol = df_temp.groupby('date')['vol'].cumsum()
    vwap = cum_tp_vol / cum_vol

    # Richiediamo una conferma su 2 candele per filtrare i falsi incroci
    for i in range(2, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        prev_close = close.iloc[i-1]
        prev2_close = close.iloc[i-2]
        c_vwap = vwap.iloc[i]
        prev_vwap = vwap.iloc[i-1]
        
        if pd.isna(c_vwap) or pd.isna(prev_vwap):
            continue
            
        if prev2_close <= prev_vwap and prev_close > prev_vwap and c_close > c_vwap:
            signals.append((current_time, "BUY", c_close))
        elif prev2_close >= prev_vwap and prev_close < prev_vwap and c_close < c_vwap:
            signals.append((current_time, "SELL", c_close))

    return signals
