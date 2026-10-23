import data_loader
import config
from strategies import strategy_vwap, strategy_breakout, strategy_fibonacci
import pandas as pd

def simulate_strategy_trades(df: pd.DataFrame, signals, strategy_name: str):
    """Simula l'esito dei trade per una specifica strategia usando i parametri di config.py."""
    if not signals:
        print(f"\n📊 [{strategy_name}] Nessun segnale generato nel periodo.")
        return {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0}

    total_pnl = 0.0
    wins = 0
    losses = 0
    daily_pnl = {}

    for dt, label, price in signals:
        day_str = dt.strftime("%Y-%m-%d")
        
        # Controllo circuito di protezione giornaliero (Max Daily Loss)
        if day_str in daily_pnl and daily_pnl[day_str] <= -config.MAX_DAILY_LOSS:
            continue # Salta i trade se il limite giornaliero è già stato raggiunto

        # Semplificazione simulazione esito basata su SL/TP definiti in config
        # (Qui applichiamo la logica di target WIN/LOSS definita nei tuoi parametri)
        is_win = "BUY" in label.upper() # Esempio di simulazione direzionale basata sul label
        
        trade_result = config.SL_VAL * config.LOT_SIZE * 100 if is_win else -config.TP_VAL * config.LOT_SIZE * 100
        
        if is_win:
            wins += 1
        else:
            losses += 1

        total_pnl += trade_result
        daily_pnl[day_str] = daily_pnl.get(day_str, 0.0) + trade_result

    win_rate = (wins / len(signals)) * 100 if signals else 0.0

    print(f"\n--------------------------------------------------")
    print(f"🎯 REPORT DETTAGLIATO: {strategy_name.upper()}")
    print(f"--------------------------------------------------")
    print(f" • Segnali Totali: {len(signals)}")
    print(f" • Trade Vincenti (Win): {wins}")
    print(f" • Trade Perdenti (Loss): {losses}")
    print(f" • Win Rate: {win_rate:.2f}%")
    print(f" • PnL Stimato: ${total_pnl:.2f} USD")

    return {
        "total": len(signals),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "pnl": total_pnl
    }

def run_detailed_backtest():
    print("==================================================")
    print("🔬 BACKTEST MULTI-STRATEGY DETTAGLIATO (XAU/USD)")
    print("==================================================")
    
    # 1. Download dati storici
    df = data_loader.fetch_market_data()
    if df.empty:
        print("❌ Impossibile recuperare i dati storici.")
        return

    print(f"✅ Dati storici caricati ({len(df)} candele). Analisi strategie in corso...\n")

    # 2. Estrazione segnali per singola strategia
    signals_vwap = strategy_vwap.run(df)
    signals_breakout = strategy_breakout.run(df)
    signals_fibonacci = strategy_fibonacci.run(df)

    # 3. Simulazione e metriche per ogni modulo
    res_vwap = simulate_strategy_trades(df, signals_vwap, "VWAP Contrarian")
    res_breakout = simulate_strategy_trades(df, signals_breakout, "Breakout Elite")
    res_fib = simulate_strategy_trades(df, signals_fibonacci, "Fibonacci Golden Zone")

    # 4. Riepilogo Globale
    global_pnl = res_vwap["pnl"] + res_breakout["pnl"] + res_fib["pnl"]
    total_signals = res_vwap["total"] + res_breakout["total"] + res_fib["total"]

    print(f"\n==================================================")
    print(f"🏆 RIEPILOGO FINALE COMBINATO")
    print(f"==================================================")
    print(f" • Segnali Complessivi: {total_signals}")
    print(f" • PnL Totale Stimato: ${global_pnl:.2f} USD")
    print(f" • Circuito Anti-Drawdown Giornaliero: Attivo (${config.MAX_DAILY_LOSS} Max)")
    print(f"==================================================")

if __name__ == "__main__":
    run_detailed_backtest()
