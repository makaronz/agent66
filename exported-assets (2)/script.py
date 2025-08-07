# Konsolidacja danych o repozytoriach GitHub podzielonych na kategorie
import pandas as pd

# Kategoria A: Wykrywanie SMC
smc_detection_repos = [
    {
        "repo": "joshyattridge/smart-money-concepts", 
        "core_tech": "Python, pandas, numpy",
        "licenses": "MIT",
        "ryzyka_integracji": "Zależność od pandas API, potencjalne zmiany w strukturze",
        "gwiazdki": 813,
        "ostatni_commit": "2025-03-03"
    },
    {
        "repo": "smtlab/smartmoneyconcepts", 
        "core_tech": "Python, indicators library",
        "licenses": "MIT", 
        "ryzyka_integracji": "Beta version, ograniczona dokumentacja",
        "gwiazdki": 3,
        "ostatni_commit": "2023-11-13"
    },
    {
        "repo": "ArunKBhaskar/PineScript-ICT-OB", 
        "core_tech": "PineScript v5",
        "licenses": "Mozilla Public License 2.0",
        "ryzyka_integracji": "Wymaga TradingView, ograniczona customizacja",
        "gwiazdki": "N/A",
        "ostatni_commit": "2023-12-12"
    }
]

# Kategoria B: Backtesting/Execution
backtesting_execution_repos = [
    {
        "repo": "freqtrade/freqtrade", 
        "core_tech": "Python, ccxt, SQLAlchemy",
        "licenses": "GPL-3.0",
        "ryzyka_integracji": "Kompleksna konfiguracja, wysokie wymagania zasobów",
        "gwiazdki": "20k+",
        "ostatni_commit": "2025-08-04"
    },
    {
        "repo": "kernc/backtesting.py", 
        "core_tech": "Python, pandas, bokeh",
        "licenses": "AGPL-3.0",
        "ryzyka_integracji": "Ograniczone multi-asset support, brak live trading",
        "gwiazdki": "5k+",
        "ostatni_commit": "2019-01-02"
    },
    {
        "repo": "backtestjs/backtestjs", 
        "core_tech": "TypeScript, Node.js",
        "licenses": "MIT",
        "ryzyka_integracji": "Ecosystem JavaScript, mniej bibliotek do analizy",
        "gwiazdki": "N/A",
        "ostatni_commit": "2024-10-02"
    }
]

# Kategoria C: RL/ML frameworks
rl_ml_frameworks_repos = [
    {
        "repo": "eomii/reinforcement-trading", 
        "core_tech": "Python, TensorFlow, CCXT",
        "licenses": "MIT",
        "ryzyka_integracji": "Fokus na market making, wymaga adaptacji do SMC",
        "gwiazdki": 32,
        "ostatni_commit": "2023-03-16"
    },
    {
        "repo": "theanh97/Deep-RL-Stock-Trading", 
        "core_tech": "Python, stable-baselines3, gymnasium",
        "licenses": "N/A",
        "ryzyka_integracji": "Academic project, może wymagać productionization",
        "gwiazdki": "N/A",
        "ostatni_commit": "2024-06-28"
    },
    {
        "repo": "D3F4LT4ST/RL-trading", 
        "core_tech": "Python, Gym, TensorFlow",
        "licenses": "N/A",
        "ryzyka_integracji": "Projekt Forex-specific, ograniczone crypto support",
        "gwiazdki": "N/A",
        "ostatni_commit": "2022-10-30"
    }
]

# Tworzenie tabel
df_smc = pd.DataFrame(smc_detection_repos)
df_backtesting = pd.DataFrame(backtesting_execution_repos)
df_rl_ml = pd.DataFrame(rl_ml_frameworks_repos)

print("🗂️ AUDYT OPEN-SOURCE - TOP 3 REPOZYTORIA W KAŻDEJ KATEGORII")
print("="*70)

print("\n📊 KATEGORIA A: WYKRYWANIE SMC")
print(df_smc[['repo', 'core_tech', 'licenses', 'gwiazdki']].to_string(index=False))

print("\n🔬 KATEGORIA B: BACKTESTING/EXECUTION") 
print(df_backtesting[['repo', 'core_tech', 'licenses', 'gwiazdki']].to_string(index=False))

print("\n🤖 KATEGORIA C: RL/ML FRAMEWORKS")
print(df_rl_ml[['repo', 'core_tech', 'licenses', 'gwiazdki']].to_string(index=False))

# Zapisanie do CSV dla dalszej analizy
all_repos = pd.concat([
    df_smc.assign(kategoria='SMC Detection'),
    df_backtesting.assign(kategoria='Backtesting/Execution'), 
    df_rl_ml.assign(kategoria='RL/ML Frameworks')
])

all_repos.to_csv('github_repos_categorized.csv', index=False)
print(f"\n✅ Dane zapisane do 'github_repos_categorized.csv'")