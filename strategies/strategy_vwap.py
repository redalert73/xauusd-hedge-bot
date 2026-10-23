# ==========================================
# STRATEGIA VWAP - ULTRA SELETTIVA (BASSA FREQUENZA)
# ==========================================

import pandas as pd
import numpy as np

def run(df):
    signals = []
    if df is None or len(df) < 50:
        return signals

    if not isinstance(df.index, pd.DatetimeIndex):
        return signals

    close = df['close']
    high = df['high']
    low = df['low']
    open_p = df['open'] if 'open' in df.columns else close
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    vol_ma = volume.rolling(window=20).mean()

    # Calcolo VWAP giornaliero
    typical_price = (high + low + close) / 3
    df_temp = pd.DataFrame({
        'tp_vol': typical_price * volume,
        'vol': volume,
        'date': df.index.date
    })
    
    cum_tp_vol = df_temp.groupby('date')['tp_vol'].cumsum()
    cum_vol = df_temp.groupby('date')['vol'].cumsum()
    vwap = cum_tp_vol / cum_vol

    for i in range(20, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_open = open_p.iloc[i]
        c_high = high.iloc[i]
        c_low = low.iloc[i]
        c_vwap = vwap.iloc[i]
        c_vol = volume.iloc[i]
        avg_vol = vol_ma.iloc[i]

        if pd.isna(c_vwap) or pd.isna(avg_vol):
            continue
            
        # Calcoliamo la distanza percentuale dal VWAP
        dist_pct = abs(c_close - c_vwap) / c_vwap

        # Filtro restrittivo: 
        # 1. Volumi superiori alla media (movimento istituzionale)
        # 2. Distanza significativa dal VWAP (esasperazione / eccesso)
        # 3. Reiezione pulita (la candela mostra un'ombra pronunciata nella direzione del rientro)
        if c_vol >= (avg_vol * 1.4) and dist_pct >= 0.0015:
            
            # Condizione SHORT: Prezzo molto sopra il VWAP ma candela debole (chiusura sotto l'apertura o lunga UPPER shadow)
            if c_close > c_vwap and (c_high - max(c_open, c_close)) > (abs(c_close - c_open) * 1.5):
                signals.append((current_time, "SELL", c_close))
                
            # Condizione LONG: Prezzo molto sotto il VWAP ma candela di reiezione (chiusura sopra l'apertura o lunga LOWER shadow)
            elif c_close < c_vwap and (min(c_open, c_close) - c_low) > (abs(c_close - c_open) * 1.5):
                signals.append((current_time, "BUY", c_close))

    return signals
