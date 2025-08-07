# Przygotowanie danych z wyszukiwań GitHub
import pandas as pd

github_repos = [
    {
        "nazwa": "joshyattridge/smart-money-concepts",
        "opis": "Python package designed for algorithmic trading with ICT's smart money concepts",
        "framework": "Python, pandas",
        "przydatnosc": 5,
        "uzasadnienie": "Kompleksowy pakiet SMC z funkcjami FVG, Order Blocks, BOS, CHOCH",
        "ostatni_commit": "2023-09-21",
        "gwiazdki": "Brak danych",
        "forki": "Brak danych"
    },
    {
        "nazwa": "vlex05/SMC-Algo-Trading",
        "opis": "Python library for building trading bots following smart money concepts",
        "framework": "Python",
        "przydatnosc": 4,
        "uzasadnienie": "Biblioteka dedykowana SMC, ale w fazie rozwoju",
        "ostatni_commit": "2022-07-24",
        "gwiazdki": "15",
        "forki": "19"
    },
    {
        "nazwa": "smtlab/smartmoneyconcepts",
        "opis": "Python package for smart money concept indicators",
        "framework": "Python",
        "przydatnosc": 4,
        "uzasadnienie": "Zawiera FVG, Order Blocks, Liquidity - kluczowe komponenty SMC",
        "ostatni_commit": "2023-11-13",
        "gwiazdki": "3",
        "forki": "0"
    },
    {
        "nazwa": "tsunafire/PineScript-SMC-Strategy",
        "opis": "Pine Script strategy based on Smart Money Concept for TradingView",
        "framework": "PineScript",
        "przydatnosc": 3,
        "uzasadnienie": "Implementacja SMC w Pine Script, przydatna do backtestów",
        "ostatni_commit": "2024-09-26",
        "gwiazdki": "Brak danych",
        "forki": "Brak danych"
    },
    {
        "nazwa": "trentstauff/FXBot",
        "opis": "Fully automated Forex trading bot with backtesting capabilities",
        "framework": "Python, OANDA API",
        "przydatnosc": 3,
        "uzasadnienie": "Framework do automatycznego tradingu, można zaadaptować do SMC",
        "ostatni_commit": "2021-05-10",
        "gwiazdki": "Brak danych",
        "forki": "Brak danych"
    },
    {
        "nazwa": "stefan-jansen/machine-learning-for-trading",
        "opis": "Comprehensive guide to ML for algorithmic trading strategies",
        "framework": "Python, TensorFlow, PyTorch",
        "przydatnosc": 5,
        "uzasadnienie": "Zaawansowane ML w tradingu, 150+ notebooków, idealne dla agenta AI",
        "ostatni_commit": "2018-05-09",
        "gwiazdki": "Brak danych",
        "forki": "Brak danych"
    },
    {
        "nazwa": "Open-Trader/opentrader",
        "opis": "Self-hosted cryptocurrency trading bot with customizable strategies",
        "framework": "JavaScript, CCXT",
        "przydatnosc": 4,
        "uzasadnienie": "Wsparcie 100+ giełd, moduły strategii, można dodać SMC",
        "ostatni_commit": "2023-12-03",
        "gwiazdki": "Brak danych",
        "forki": "Brak danych"
    },
    {
        "nazwa": "enarjord/passivbot",
        "opis": "Contrarian market maker bot for perpetual futures",
        "framework": "Python, Rust",
        "przydatnosc": 3,
        "uzasadnienie": "Zaawansowany bot futures, market making - uzupełnienie dla SMC",
        "ostatni_commit": "2020-12-11",
        "gwiazdki": "Brak danych",
        "forki": "Brak danych"
    },
    {
        "nazwa": "mariaoxulz/smctorgnkcc",
        "opis": "SMC Trading Bot comparison and automated execution",
        "framework": "Web-based platforms",
        "przydatnosc": 2,
        "uzasadnienie": "Porównanie platform, ale nie open-source kod",
        "ostatni_commit": "2025-05-11",
        "gwiazdki": "Brak danych",
        "forki": "Brak danych"
    },
    {
        "nazwa": "Gifted87/TradingBot",
        "opis": "Forex and Crypto analyzer with SMC analysis and Wyckoff patterns",
        "framework": "Python (przypuszczenie)",
        "przydatnosc": 4,
        "uzasadnienie": "Zawiera SMC, analizę order flow, manipulację płynności",
        "ostatni_commit": "2025-01-18",
        "gwiazdki": "Brak danych",
        "forki": "Brak danych"
    }
]

# Konwersja do DataFrame
df_github = pd.DataFrame(github_repos)
print("GitHub Repositories - SMC Trading:")
print(df_github[['nazwa', 'framework', 'przydatnosc', 'ostatni_commit', 'gwiazdki', 'forki']].to_string(index=False))