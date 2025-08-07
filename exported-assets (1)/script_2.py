# Przygotowanie tabeli porównawczej źródeł
import pandas as pd

sources_comparison = [
    # GitHub Sources
    {"Źródło": "joshyattridge/smart-money-concepts", "Typ": "GitHub", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Python", "Przydatność": 5},
    {"Źródło": "stefan-jansen/ml-trading", "Typ": "GitHub", "Wsparcie/Opór": "Tak", "Trend duration": "Częściowo", "Trend reversal": "Tak", "Liquidity/CHOCH": "Nie", "Order blocks": "Nie", "Język": "Python", "Przydatność": 5},
    {"Źródło": "vlex05/SMC-Algo-Trading", "Typ": "GitHub", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Python", "Przydatność": 4},
    {"Źródło": "smtlab/smartmoneyconcepts", "Typ": "GitHub", "Wsparcie/Opór": "Tak", "Trend duration": "Częściowo", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Python", "Przydatność": 4},
    {"Źródło": "Open-Trader/opentrader", "Typ": "GitHub", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Nie", "Order blocks": "Nie", "Język": "JavaScript", "Przydatność": 4},
    {"Źródło": "tsunafire/PineScript-SMC", "Typ": "GitHub", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "PineScript", "Przydatność": 3},
    {"Źródło": "trentstauff/FXBot", "Typ": "GitHub", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Nie", "Order blocks": "Nie", "Język": "Python", "Przydatność": 3},
    {"Źródło": "enarjord/passivbot", "Typ": "GitHub", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Nie", "Order blocks": "Nie", "Język": "Python/Rust", "Przydatność": 3},
    
    # Reddit Sources - reprezentatywne posty
    {"Źródło": "r/Daytrading SMC Strategy", "Typ": "Reddit", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 4},
    {"Źródło": "r/Forex SMC Discussion", "Typ": "Reddit", "Wsparcie/Opór": "Tak", "Trend duration": "Częściowo", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 3},
    {"Źródło": "r/Trading Price Action vs SMC", "Typ": "Reddit", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Częściowo", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 3},
    {"Źródło": "r/InnerCircleTraders", "Typ": "Reddit", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 3},
    
    # Web Sources - kluczowe artykuły
    {"Źródło": "EarnForex SMC Flaws", "Typ": "Web", "Wsparcie/Opór": "Tak", "Trend duration": "Częściowo", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 4},
    {"Źródło": "PhotonTradingFX SMC Guide", "Typ": "Web", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 4},
    {"Źródło": "MindMathMoney Structure", "Typ": "Web", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 4},
    {"Źródło": "FTMO SMC Trading", "Typ": "Web", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 4},
    {"Źródło": "TradingView LuxAlgo OB", "Typ": "Web", "Wsparcie/Opór": "Tak", "Trend duration": "Częściowo", "Trend reversal": "Tak", "Liquidity/CHOCH": "Nie", "Order blocks": "Tak", "Język": "PineScript", "Przydatność": 3},
    {"Źródło": "BankOfEngland Algo Regulation", "Typ": "Web", "Wsparcie/Opór": "Nie", "Trend duration": "Nie", "Trend reversal": "Nie", "Liquidity/CHOCH": "Nie", "Order blocks": "Nie", "Język": "Regulacje", "Przydatność": 2},
    
    # Academic/Research
    {"Źródło": "IJNRD Adaptive Algo Trading", "Typ": "Academic", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Python", "Przydatność": 5},
    
    # YouTube/Educational
    {"Źródło": "CodeTrading CHOCH Python", "Typ": "YouTube", "Wsparcie/Opór": "Częściowo", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Nie", "Język": "Python", "Przydatność": 4},
    {"Źródło": "Various SMC Tutorials", "Typ": "YouTube", "Wsparcie/Opór": "Tak", "Trend duration": "Tak", "Trend reversal": "Tak", "Liquidity/CHOCH": "Tak", "Order blocks": "Tak", "Język": "Koncepcyjny", "Przydatność": 3}
]

df_comparison = pd.DataFrame(sources_comparison)
print("Tabela porównawcza źródeł:")
print(df_comparison.to_string(index=False))

# Zapisz jako CSV
df_comparison.to_csv('smc_sources_comparison.csv', index=False)
print(f"\nTabela zapisana jako CSV. Łączna liczba źródeł: {len(sources_comparison)}")