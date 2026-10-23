# ==========================================
# STRATEGIA VWAP - HIGHER WIN RATE (SELETTIVA)
# ==========================================

import pandas as pd
import numpy as np

def run(df):
    signals = []
    if df is None or len(df) < 25:
        return signals

    if not isinstance(df.index, pd.DatetimeIndex):
        return signals

    close = df['close']
    high = df['high']
    low = df['low']
    open_p = df['open'] if 'open' in df.columns else close
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

    for i in range(15, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_open = open_p.iloc[i]
        c_vwap = vwap.iloc[i]

        if pd.isna(c_vwap):
            continue
            
        dist_pct = abs(c_close - c_vwap) / c_vwap

        # Deviazione pulita unita a candela di inversione decisa
        if dist_pct >= 0.0012:
            # BUY se il prezzo è sotto VWAP con candela rialzista di reiezione
            if c_close < c_vwap and c_close > c_open and close.iloc[i-1] < open_p.iloc[i-1]:
                signals.append((current_time, "BUY", c_close))
            # SELL se il prezzo è sopra VWAP con candela ribassista di reiezione
            elif c_close > c_vwap and c_close < c_open and close.iloc[i-1] > open_p.iloc[i-1]:
                signals.append((current_time, "SELL", c_close))

    return signals
