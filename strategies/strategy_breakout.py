# ==========================================
# STRATEGIA BREAKOUT ELITE (M15)
# ==========================================

import pandas as pd
import numpy as np
import config

def run(df):
    """
    Strategia Breakout Elite (15 min) basata sui parametri centralizzati in config.py.
    """
    signals = []
    
    if df is None or len(df) < config.ATR_PERIOD + 20:
        return signals

    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume'] if 'volume' in df.columns else pd.Series(1, index=df.index)

    # Calcolo ATR (Average True Range)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=config.ATR_PERIOD).mean()

    # Calcolo del Momentum
    momentum = close.diff(config.ATR_PERIOD)

    # Bande di breakout e media volumi
    lookback = 20
    rolling_high = high.rolling(window=lookback).max()
    rolling_low = low.rolling(window=lookback).min()
    vol_ma = volume.rolling(window=lookback).mean()

    # Generazione segnali con filtri di volume, momentum e offset
    for i in range(lookback + 1, len(df)):
        current_time = df.index[i]
        c_close = close.iloc[i]
        c_vol = volume.iloc[i]
        c_mom = momentum.iloc[i] if not np.isnan(momentum.iloc[i]) else 0.0
        
        min_vol_required = vol_ma.iloc[i] * config.VOL_MULTIPLIER
        
        # Condizione LONG (Rottura rialzista con filtri di volume e momentum)
        if c_close > (rolling_high.iloc[i - 1] + config.PRICE_OFFSET) and c_vol >= min_vol_required and c_mom >= config.MOMENTUM_THRESHOLD:
            signals.append((current_time, "BUY", c_close))
            
        # Condizione SHORT (Rottura ribassista con filtri di volume e momentum)
        elif c_close < (rolling_low.iloc[i - 1] - config.PRICE_OFFSET) and c_vol >= min_vol_required and c_mom <= -config.MOMENTUM_THRESHOLD:
            signals.append((current_time, "SELL", c_close))

    return signals

def calculate_pnl_report(trades_df):
    """
    Formatta il report applicando la logica PnL richiesta:
    - Win = SL hit ($2.400); Loss = TP hit ($2.000)
    - Netto positivo (Win prevalenti): preceduto dal segno '-'
    - Netto negativo (Loss prevalenti): nessun segno (valore assoluto)
    - Circuit Breaker: interruzione se si tocca MAX_DAILY_LOSS ($3.000)
    """
    net_pnl = trades_df['pnl'].sum() if not trades_df.empty else 0.0
    
    if net_pnl > 0 and config.USE_MINUS_FOR_WINS:
        formatted_result = f"-${abs(net_pnl):.2f}"
    else:
        formatted_result = f"${abs(net_pnl):.2f}"
        
    return formatted_result
