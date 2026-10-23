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

    for i in range(2, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        prev_close = close.iloc[i-1]
        c_vwap = vwap.iloc[i]
        prev_vwap = vwap.iloc[i-1]
        c_ema = ema50.iloc[i]
        
        if pd.isna(c_vwap) or pd.isna(prev_vwap) or pd.isna(c_ema):
            continue
            
        # Filtro di pendenza del VWAP per assicurarci che il trend sia direzionale e non piatto
        vwap_slope = c_vwap - vwap.iloc[i-2]
        min_distance = c_close * 0.0008  # Distanza minima dello 0.08% dal VWAP

        if abs(c_close - c_vwap) >= min_distance:
            # LONG: Taglio dal basso verso l'alto con EMA favorevole e VWAP in salita
            if prev_close <= prev_vwap and c_close > c_vwap and c_close > c_ema and vwap_slope > 0:
                signals.append((current_time, "BUY", c_close))
            # SHORT: Taglio dall'alto verso il basso con EMA favorevole e VWAP in discesa
            elif prev_close >= prev_vwap and c_close < c_vwap and c_close < c_ema and vwap_slope < 0:
                signals.append((current_time, "SELL", c_close))

    return signals
