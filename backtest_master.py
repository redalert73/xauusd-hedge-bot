import pandas as pd
from backtest_detailed import run_detailed_backtest

def load_market_data():
    """
    Funzione di caricamento dei dati di mercato storici (Candele XAU/USD).
    Sostituire o integrare con il caricamento da CSV/API reale.
    """
    try:
        # Esempio di lettura dati se presenti in file locale o generati
        # df = pd.read_csv('market_data.csv')
        # return df
        pass
    except Exception as e:
        print(f"⚠️ Errore caricamento dati: {e}")
    return pd.DataFrame()

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

    # Caricamento dataset candele
    df_candles = load_market_data()
    
    strategies = ['Breakout Elite', 'VWAP Strategy', 'Fibonacci Strategy']
    summary_data = []

    for strat in strategies:
        print(f"⚙️ [MASTER] Richiesta analisi dettagliata per: {strat}")
        
        # Esecuzione backtest dettagliato sul set di dati
        df_results = run_detailed_backtest(df_candles, strat)
        
        if not df_results.empty:
            total_trades = len(df_results)
            tp_wins = len(df_results[df_results['result'] == 'TP'])
            sl_losses = len(df_results[df_results['result'] == 'SL'])
            net_pnl = df_results['pnl ($)'].sum()
            violations = len(df_results[df_results['single_trade_breached'] == True])
        else:
            total_trades = 0
            tp_wins = 0
            sl_losses = 0
            net_pnl = 0.0
            violations = 0

        summary_data.append({
            'Strategy': strat,
            'Total Trades': total_trades,
            'TP Wins': tp_wins,
            'SL Losses': sl_losses,
            'Net PnL ($)': net_pnl,
            'Single Trade Violations': violations
        })

    print("\n============================================================")
    print("📋 [ACTION REPORT] RIEPILOGO COMPLESSIVO - BACKTEST MASTER")
    print("============================================================")
    df_summary = pd.DataFrame(summary_data)
    print(df_summary.to_string(index=False))
    print("============================================================")

if __name__ == '__main__':
    main()
