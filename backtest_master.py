import pandas as pd
from backtest_detailed import run_detailed_backtest

def main():
    print("============================================================")
    print("🚀 [ACTION TYPE: BACKTEST MASTER] - AVVIO COORDINATORE")
    print("============================================================")
    print("🔹 Parametri Operativi Bloccati:")
    print("- Lotto: 1.04")
    print("- Stop Loss (SL): -$2,400.0 USD")
    print("- Take Profit (TP): $2,000.0 USD")
    print("- Limite Singolo Trade (Slippage): -$2,800.0 USD (Aggiornato)")
    print("- Modalità: Stress-Test Avverso (Priorità SL)")
    print("============================================================\n")

    # Inserisci o richiama il caricamento dei dati delle candele (df_candles)
    # df_results = run_detailed_backtest(df_candles, 'Breakout Elite')

if __name__ == '__main__':
    main()
