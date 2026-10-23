import pandas as pd
import numpy as np

def run(df: pd.DataFrame):
    """
    Breakout Elite Strategy (Configurazione Max Win Rate ~65%)
    Struttura modulare compatibile con main.py e backtest_detailed.py.
    """
    if df.empty or len(df) < 50:
        return []

    signals = []
    df = df.copy()

    # 1. Canale Donchian di riferimento (20 periodi)
    window = 20
    df['upper_channel'] = df['high'].shift(1).rolling(window=window).max()
    df['lower_channel'] = df['low'].shift(1).rolling(window=window).min()

    # 2. Filtro Trend Macro (EMA 200 periodi)
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

    # 3. Buffer Anti-Fakeout (0.35 = 35 pips di margine)
    buffer = 0.35

    for i in range(window, len(df)):
        row = df.iloc[i]
        dt = pd.to_datetime(row['datetime'])

        # Filtro orario operativo: 06:00 - 20:30 UTC
        if not (6 <= dt.hour < 20 or (dt.hour == 20 and dt.minute <= 30)):
            continue

        price = row['close']
        upper_level = row['upper_channel']
        lower_level = row['lower_channel']
        ema = row['ema_200']

        if pd.isna(upper_level) or pd.isna(lower_level) or pd.isna(ema):
            continue

        # BREAKOUT BUY: Rottura confermata sopra canale + buffer ED in trend rialzista (Prezzo > EMA200)
        if price > (upper_level + buffer) and price > ema:
            signals.append((dt, "BREAKOUT_BUY", price))

        # BREAKOUT SELL: Rottura confermata sotto canale - buffer ED in trend ribassista (Prezzo < EMA200)
        elif price < (lower_level - buffer) and price < ema:
            signals.append((dt, "BREAKOUT_SELL", price))

    return signals
