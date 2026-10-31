# ==========================================
# CONVERTITORE CSV -> formato del backtest (datetime,open,high,low,close in UTC, M5)
# ==========================================
# Accetta:
#   - Dukascopy ("Gmt time,Open,High,Low,Close,Volume", es. 01.03.2024 10:05:00.000) - scegli fuso GMT/UTC
#   - MetaTrader 5 (History Center -> Export: <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> ...)
#     ATTENZIONE: MT5 esporta nell'ora del SERVER del broker. La maggior parte dei server usa "New York + 7 ore"
#     (UTC+2 d'inverno, UTC+3 d'estate americana): usa --server-ny. Se il tuo e' a offset fisso usa --offset-ore.
#   - Qualsiasi CSV con colonne datetime/open/high/low/close
# Se i dati sono M1 li raggruppa in M5.
#
# Uso: python convert_csv.py ingresso.csv uscita.csv [--server-ny | --offset-ore N]
#      poi: python backtest_hedge.py --csv uscita.csv    e    python edge_scan.py --csv uscita.csv

import argparse
import re

import pandas as pd


def read_any(path):
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        head = f.readline()
    sep = "\t" if head.count("\t") >= head.count(",") and head.count("\t") > 0 else ("," if head.count(",") >= head.count(";") else ";")
    df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
    df.columns = [re.sub(r"[<>\s]", "", str(c)).lower() for c in df.columns]
    return df


def to_frame(df):
    cols = set(df.columns)
    if {"date", "time"} <= cols:                                   # MetaTrader 5
        ts = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), errors="coerce")
    else:
        tcol = next((c for c in df.columns if c in ("datetime", "gmttime", "time", "timestamp", "date")), df.columns[0])
        raw = df[tcol].astype(str)
        dayfirst = raw.str.match(r"^\d{2}\.\d{2}\.\d{4}").mean() > 0.5   # Dukascopy: 01.03.2024 10:05:00.000
        ts = pd.to_datetime(raw, dayfirst=dayfirst, errors="coerce")
    out = pd.DataFrame({
        "datetime": ts,
        "open": pd.to_numeric(df["open"], errors="coerce"),
        "high": pd.to_numeric(df["high"], errors="coerce"),
        "low": pd.to_numeric(df["low"], errors="coerce"),
        "close": pd.to_numeric(df["close"], errors="coerce"),
    }).dropna()
    return out.drop_duplicates("datetime").sort_values("datetime")


def to_m5(out):
    out = out.set_index("datetime")
    step = out.index.to_series().diff().median()
    if step is not pd.NaT and step < pd.Timedelta(minutes=5):
        out = out.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return out.reset_index()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--server-ny", action="store_true", help="ora server = New York + 7 ore (cambia con l'ora legale USA)")
    ap.add_argument("--offset-ore", type=float, default=0.0, help="ore da SOTTRARRE per ottenere UTC (es. 2 se il file e' in UTC+2)")
    a = ap.parse_args()
    out = to_m5(to_frame(read_any(a.src)))
    if a.server_ny:
        ny = (out["datetime"] - pd.Timedelta(hours=7)).dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward")
        out["datetime"] = ny.dt.tz_convert("UTC").dt.tz_localize(None)
        out = out.dropna(subset=["datetime"])
    else:
        out["datetime"] = out["datetime"] - pd.Timedelta(hours=a.offset_ore)
    out.to_csv(a.dst, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"{len(out)} candele M5 dal {out['datetime'].min()} al {out['datetime'].max()} (UTC) -> {a.dst}")
