import pandas as pd

def run(df: pd.DataFrame):
    """
    Breakout Elite Strategy (Configurazione ad Alta Precisione Anti-Fakeout)
    Richiede un canale Donchian esteso e un buffer di 50 pips per eliminare i falsi segnali.
    """
    if df.empty or len(df) < 30:
        return []

    signals = []
    df = df.copy()

    # Canale Donchian di lungo periodo per selezionare solo livelli chiave
    window = 24
    df['upper_channel'] = df['high'].shift(1).rolling(window=window).max()
    df['lower_channel'] = df['low'].shift(1).rolling(window=window).min()

    # Buffer anti-fakeout stringente (0.50 = 50 pips di rottura confermata)
    buffer = 0.50

    for i in range(window, len(df)):
        row = df.iloc[i]
        dt = pd.to_datetime(row['datetime'])

        # Filtro orario operativo: 06:00 - 20:30 UTC
        if not (6 <= dt.hour < 20 or (dt.hour == 20 and dt.minute <= 30)):
            continue

        price = row['close']
        upper_level = row['upper_channel']
        lower_level = row['lower_channel']

        # Verifica rottura pulita oltre il margine di sicurezza
        if pd.notna(upper_level) and price > (upper_level + buffer):
            signals.append((dt, "BREAKOUT_BUY", price))
        elif pd.notna(lower_level) and price < (lower_level - buffer):
            signals.append((dt, "BREAKOUT_SELL", price))

    return signals
