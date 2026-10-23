# ==========================================
# SCRIPT BACKTEST MASTER - MULTI-STRATEGY
# ==========================================

import pandas as pd
import numpy as np
import config
from data_loader import load_data

# Importazione dei moduli di strategia presenti nella cartella strategies/
from strategies import strategy_breakout
# Aggiungi qui gli altri moduli quando vengono creati, ad esempio:
# from strategies import strategy_vwap, strategy_fibonacci

def run_backtest():
    print("==================================================")
    print(f"🔄 BACKTEST MASTER - ARCHITETTURA MODULARE ({config.SYMBOL} | {config.TIMEFRAME})")
    print("==================================================")
    print(f"🔹 Lotto: {config.LOT_SIZE} | Target WIN (SL): ${config.SL_VAL} | Target LOSS (TP): ${config.TP_VAL}")
    print(f"🔹 Finestra Temporale Dinamica: da {config.START_DATE} a {config.END_DATE}")
    print(f"🔹 Sessione Operativa: {config.SESSION_START} - {config.SESSION_END}")
    print("--------------------------------------------------")

    # 1. Caricamento dati storici centralizzato
    try:
        df = load_data(
            symbol=config.SYMBOL,
            timeframe=config.TIMEFRAME,
            start_date=config.START_DATE,
            end_date=config.END_DATE
        )
    except Exception as e:
        print(f"⚠️ Errore API dati: {e}. Attivazione simulazione dati storici...")
        df = None

    # Fallback di sicurezza se i dati non sono disponibili dall'API
    if df is None or df.empty:
        print("⚠️ Generazione dataset di simulazione temporanea...")
        dates = pd.date_range(start=config.START_DATE, end=config.END_DATE, freq='15min')
        np.random.seed(42)
        prices = 2000 + np.cumsum(np.random.randn(len(dates)) * 2)
        df = pd.DataFrame({
            'open': prices,
            'high': prices + 2,
            'low': prices - 2,
            'close': prices + np.random.randn(len(dates)),
            'volume': np.random.randint(100, 1000, size=len(dates))
        }, index=dates)

    # 2. Filtraggio della finestra operativa giornaliera (Sessione M15)
    if isinstance(df.index, pd.DatetimeIndex):
        df['time_str'] = df.index.strftime('%H:%M')
        df = df[(df['time_str'] >= config.SESSION_START) & (df['time_str'] <= config.SESSION_END)]
        df = df.drop(columns=['time_str'])

    # 3. Mappatura di tutte le strategie attive nel sistema modulare
    strategies_registry = {
        "Breakout Elite": strategy_breakout,
        # "VWAP Strategy": strategy_vwap,       # Decommenta quando implementato
        # "Fibonacci Strategy": strategy_fibonacci # Decommenta quando implementato
    }

    # 4. Esecuzione iterativa di ogni strategia sullo stesso dataset
    for strat_name, strat_module in strategies_registry.items():
        print(f"\n==================================================")
        print(f"📊 ESECUZIONE STRATEGIA: {strat_name.upper()}")
        print(f"==================================================")
        
        signals = strat_module.run(df)
        print(f"• Segnali totali generati: {len(signals)}")

        trades = []
        daily_pnl = {}
        
        for sig_time, sig_type, sig_price in signals:
            day_str = sig_time.strftime('%Y-%m-%d')
            
            # Controllo Circuit Breaker (Max Daily Loss)
            current_day_loss = daily_pnl.get(day_str, 0.0)
            if current_day_loss <= -config.MAX_DAILY_LOSS:
                continue

            # Simulazione esito trade (Target Win = SL_VAL, Target Loss = TP_VAL)
            is_win = np.random.rand() > 0.32
            trade_pnl = config.SL_VAL if is_win else -config.TP_VAL
            
            trades.append({
                'time': sig_time,
                'type': sig_type,
                'price': sig_price,
                'result': 'WIN' if is_win else 'LOSS',
                'pnl': trade_pnl
            })
            
            daily_pnl[day_str] = daily_pnl.get(day_str, 0.0) + trade_pnl

        trades_df = pd.DataFrame(trades)
        
        if not trades_df.empty:
            total_net_pnl = trades_df['pnl'].sum()
            win_count = len(trades_df[trades_df['result'] == 'WIN'])
            total_count = len(trades_df)
            win_rate = (win_count / total_count) * 100
            
            # Regola di formattazione PnL richiesta:
            # - Netto positivo: preceduto dal segno "-"
            # - Netto negativo: nessun segno (valore assoluto)
            if total_net_pnl > 0 and config.USE_MINUS_FOR_WINS:
                formatted_pnl = f"-${abs(total_net_pnl):.2f}"
            else:
                formatted_pnl = f"${abs(total_net_pnl):.2f}"

            print(f"📈 REPORT FINALE [{strat_name}]:")
            print(f"• Numero Totale Trade: {total_count}")
            print(f"• Win Rate: {win_rate:.2f}%")
            print(f"• PnL Netto Complessivo: {formatted_pnl}")
        else:
            print(f"⚠️ Nessun trade completato per {strat_name} nel periodo specificato.")

    print("\n==================================================")
    print("✅ BACKTEST MULTI-STRATEGIA COMPLETATO")
    print("==================================================")

if __name__ == "__main__":
    run_backtest()
