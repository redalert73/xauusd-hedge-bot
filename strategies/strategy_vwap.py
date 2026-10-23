# ==========================================
# STRATEGIA VWAP (M5) - ULTRA SELETTIVA
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    signals = []
    if df is None or len(df) < 50:
        return signals

    if not isinstance(df.index, pd.DatetimeIndex):
        return signals

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    ema50 = close.ewm(span=50, adjust=False).mean()

    typical_price = (high + low + close) / 3
    df_temp = pd.DataFrame({
        'tp_vol': typical_price * volume,
        'vol': volume,
        'date': df.index.date
    })
    
    cum_tp_vol = df_temp.groupby('date')['tp_vol'].cumsum()
    cum_vol = df_temp.groupby('date')['vol'].cumsum()
    vwap = cum_tp_vol / cum_vol

    for i in range(5, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        prev_close = close.iloc[i-1]
        c_vwap = vwap.iloc[i]
        prev_vwap = vwap.iloc[i-1]
        c_ema = ema50.iloc[i]
        
        if pd.isna(c_vwap) or pd.isna(prev_vwap) or pd.isna(c_ema):
            continue
            
        # Distanza minima percentuale dal VWAP per evitare il rumore laterale
        min_dist = c_close * 0.0015
        
        if abs(c_close - c_vwap) >= min_dist:
            # Richiediamo che le ultime 3 candele confermino la direzione rispetto al VWAP e all'EMA
            if (prev_close <= prev_vwap and c_close > c_vwap and 
                close.iloc[i-2] <= vwap.iloc[i-2] and close.iloc[i-3] <= vwap.iloc[i-3] and 
                c_close > c_ema):
                signals.append((current_time, "BUY", c_close))
            elif (prev_close >= prev_vwap and c_close < c_vwap and 
                  close.iloc[i-2] >= vwap.iloc[i-2] and close.iloc[i-3] >= vwap.iloc[i-3] and 
                  c_close < c_ema):
                signals.append((current_time, "SELL", c_close))

    return signals
