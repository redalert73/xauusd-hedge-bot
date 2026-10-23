import data_loader
from strategies import strategy_vwap, strategy_breakout, strategy_fibonacci

def main():
    print("==================================================")
    print("🚀 MULTI-STRATEGY SCANNER MODULARE (XAU/USD)")
    print("==================================================")
    
    # 1. Download dati centralizzato (Unica chiamata API)
    df = data_loader.fetch_market_data()
    if df.empty:
        print("❌ Impossibile recuperare i dati di mercato. Interrompo.")
        return

    print(f"✅ Dati caricati correttamente ({len(df)} candele). Esecuzione strategie in memoria...\n")

    # 2. Esecuzione dinamica di tutti i moduli di strategia
    signals = []
    signals.extend(strategy_vwap.run(df))
    signals.extend(strategy_breakout.run(df))
    signals.extend(strategy_fibonacci.run(df))

    # 3. Ordinamento cronologico e report pulito
    signals.sort(key=lambda x: x[0])

    print(f"📊 REPORT SEGNALI ATTIVI (Totale: {len(signals)})")
    print("--------------------------------------------------")
    for dt, label, price in signals:
        print(f"[{dt}] {label} | Prezzo: {price}")
    print("==================================================")

if __name__ == "__main__":
    main()
