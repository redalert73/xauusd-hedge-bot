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

    # Calcoliamo anche una deviazione/ATR di supporto per filtrare il rumore vicino al VWAP
    for i in range(2, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        prev_close = close.iloc[i-1]
        c_vwap = vwap.iloc[i]
        prev_vwap = vwap.iloc[i-1]
        
        if pd.isna(c_vwap) or pd.isna(prev_vwap):
            continue
            
        # Distanza minima dal VWAP per evitare falsi incroci continui nel "rumore" laterale
        distance = abs(c_close - c_vwap)
        min_distance = c_close * 0.0005  # 0.05% di distanza minima dal prezzo

        if distance >= min_distance:
            if prev_close <= prev_vwap and c_close > c_vwap:
                signals.append((current_time, "BUY", c_close))
            elif prev_close >= prev_vwap and c_close < c_vwap:
                signals.append((current_time, "SELL", c_close))

    return signals
