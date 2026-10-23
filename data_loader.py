import os
import requests
import pandas as pd
import config

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

def fetch_market_data() -> pd.DataFrame:
    """Scarica i dati storici da Twelve Data una sola volta per tutte le strategie."""
    if not TWELVE_DATA_API_KEY:
        print("⚠️ TWELVE_DATA_API_KEY non trovata nelle variabili d'ambiente.")
        return pd.DataFrame()

    url = f"https://api.twelvedata.com/time_series?symbol={config.SYMBOL}&interval={config.INTERVAL}&outputsize=500&apikey={TWELVE_DATA_API_KEY}"
    try:
        res = requests.get(url, timeout=15).json()
        if "values" in res:
            df = pd.DataFrame(res["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            
            # Conversione sicura dei prezzi
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            # Gestione opzionale del volume senza forzature
            if "volume" in df.columns:
                try:
                    df["volume"] = df["volume"].astype(float)
                except Exception:
                    pass

            df = df.sort_values("datetime").reset_index(drop=True)
            return df
    except Exception as e:
        print(f"⚠️ Errore di connessione API: {e}")
    
    return pd.DataFrame()
