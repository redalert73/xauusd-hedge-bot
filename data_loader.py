# ==========================================
# DATA LOADER - TWELVE DATA API
# ==========================================

import os
import requests
import pandas as pd
import config

def load_data(symbol=config.SYMBOL, timeframe=config.TIMEFRAME, start_date=config.START_DATE, end_date=config.END_DATE):
    """
    Carica i dati storici da Twelve Data API utilizzando la configurazione globale.
    In caso di errore o assenza di chiave API, solleva un'eccezione per attivare il fallback nel master.
    """
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        raise ValueError("TWELVE_DATA_API_KEY non trovata nelle variabili d'ambiente.")

    url = "https://api.twelvedata.com/time_series"
    
    params = {
        "symbol": symbol,
        "interval": timeframe,
        "outputsize": 5000,  # Massimo storico o finestra desiderata
        "apikey": api_key,
        "format": "JSON"
    }

    print(f"✅ TWELVE_DATA_API_KEY rilevata. Scaricamento dati da Twelve Data per {symbol} ({timeframe})...")
    
    response = requests.get(url, params=params)
    data = response.json()

    if "code" in data and data["code"] != 200:
        raise Exception(f"Errore API Twelve Data: {data.get('message', 'Errore sconosciuto')}")

    if "values" not in data:
        raise Exception("Nessun dato 'values' trovato nella risposta di Twelve Data.")

    df = pd.DataFrame(data["values"])
    
    # Conversione e pulizia del DataFrame
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df = df.sort_index()

    # Conversione colonne numeriche
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:
            if col == 'volume':
                df['volume'] = 100.0  # Fallback volume se assente
            else:
                df[col] = df['close']

    # Filtraggio basato sulle date start e end dinamiche
    if start_date and end_date:
        df = df.loc[start_date:end_date]

    return df
