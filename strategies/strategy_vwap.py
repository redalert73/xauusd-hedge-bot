# ==========================================
# STRATEGIA VWAP - TARGET: INVERSIONE SUI PICCHI (SL)
# ==========================================

import pandas as pd
import numpy as np

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

    for i in range(5, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_vwap = vwap.iloc[i]
        
        if pd.isna(c_vwap):
            continue

        # Entriamo long sui massimi estremi sopra il VWAP (esasperazione) -> il prezzo crolla e prende lo SL
        if c_close > (c_vwap * 1.003) and close.iloc[i-1] > c_close:
            signals.append((current_time, "BUY", c_close))
        # Entriamo short sui minimi estremi sotto il VWAP -> il prezzo rimbalza e prende lo SL
        elif c_close < (c_vwap * 0.997) and close.iloc[i-1] < c_close:
            signals.append((current_time, "SELL", c_close))

    return signals
