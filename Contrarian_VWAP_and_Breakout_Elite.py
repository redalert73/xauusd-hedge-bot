import os
import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import config

# API Key per recuperare i dati da Twelve Data
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

def fetch_data():
    """Scarica i dati storici da Twelve Data in modo sicuro."""
    if not TWELVE_DATA_API_KEY:
        print("⚠️ TWELVE_DATA_API_KEY non trovata nelle variabili d'ambiente.")
        return pd.DataFrame()

    url = f"https://api.twelvedata.com/time_series?symbol={config.SYMBOL}&interval={config.INTERVAL}&outputsize=500&apikey={TWELVE_DATA_API_KEY}"
    try:
        res = requests.get(url, timeout=15).json()
        if "values" in res:
            df = pd.DataFrame(res["values"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            
            # Conversione sicura solo delle colonne di prezzo effettivamente presenti
            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            # Gestione sicura del volume (se assente, non genera errore)
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

def run_bot_cycle(daily_loss_tracker=0.0):
    print("=== Contrarian VWAP & Breakout Elite Bot Avviato (Config Centralizzata) ===")
    
    df = fetch_data()
    if df.empty:
        print("❌ Impossibile recuperare i dati di mercato. Ciclo saltato.")
        return daily_loss_tracker

    # Calcolo VWAP e Breakout
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    if "volume" in df.columns and df["volume"].sum() > 0:
        df["vwap"] = (df["typical_price"] * df["volume"]).cumsum() / df["volume"].cumsum()
    else:
        df["vwap"] = df["typical_price"].rolling(window=14).mean()

    lookback = 20
    df["resistance"] = df["high"].rolling(window=lookback).max().shift(1)
    df["support"] = df["low"].rolling(window=lookback).min().shift(1)

    signals = []
    for i in range(lookback + 1, len(df)):
        row = df.iloc[i]
        dt = row["datetime"]
        
        current_mins = dt.hour * 60 + dt.minute
        if not (config.ORA_INIZIO_MINUTI <= current_mins <= config.ORA_FINE_MINUTI):
            continue

        # Segnali VWAP Contrarian
        if row["close"] < row["vwap"] * 0.998:
            signals.append((dt, "[VWAP] BUY (Contrarian)", row["close"]))
        elif row["close"] > row["vwap"] * 1.002:
            signals.append((dt, "[VWAP] SELL (Contrarian)", row["close"]))

        # Segnali Breakout Elite
        if row["close"] > row["resistance"]:
            signals.append((dt, "[BREAKOUT] BUY (Resistenza rotta)", row["close"]))
        elif row["close"] < row["support"]:
            signals.append((dt, "[BREAKOUT] SELL (Supporto rotto)", row["close"]))

    print(f"📊 Analisi completata. Candele elaborate: {len(df)} | Segnali totali rilevati: {len(signals)}")
    for dt, label, price in signals[-5:]:  # Mostra gli ultimi 5 segnali rilevati
        print(f"[{dt}] {label} | Prezzo: {price}")

    return daily_loss_tracker

if __name__ == "__main__":
    run_bot_cycle()
