# Przygotowanie danych Reddit z analizy wyszukiwań
reddit_posts = [
    {
        "tytul": "I studied ICT/Smart Money Concepts For 4 Months",
        "data": "2023-06-02",
        "upvotes": "Brak danych",
        "komentarze": "Wiele",
        "opis": "Krytyczna analiza SMC - większość to przepakowane tradycyjne koncepcje",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "Price Action or Smart Money Concept (SMC)? Need Help Deciding!",
        "data": "2024-04-15",
        "upvotes": "Brak danych",
        "komentarze": "Średnio",
        "opis": "Porównanie Price Action vs SMC, dyskusja o wyborze strategii",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "Smart Money Concepts is for FOOLS",
        "data": "2023-10-05",
        "upvotes": "Brak danych",
        "komentarze": "Wysokie",
        "opis": "Kontrowersyjne stanowisko przeciw SMC, dyskusja o efektywności",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "Do SMC strategies really work?",
        "data": "2023-12-29",
        "upvotes": "Brak danych",
        "komentarze": "Średnio",
        "opis": "Pytanie o skuteczność strategii SMC, mixed opinions",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "Is Smart Money Trading Just Overcomplicated Price Action?",
        "data": "2024-12-28",
        "upvotes": "8",
        "komentarze": "17",
        "opis": "Analiza czy SMC to skomplikowane price action z nową terminologią",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "Preview of automated entries. SMC trading",
        "data": "2024-12-29",
        "upvotes": "1",
        "komentarze": "Niskie",
        "opis": "Prezentacja semi-automated swing trading system z SMC",
        "kod_indykator": "Tak"
    },
    {
        "tytul": "How I trade Smart Money Concept",
        "data": "2024-10-27",
        "upvotes": "59",
        "komentarze": "27",
        "opis": "Opis prostej strategii SMC z supply/demand zones",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "I just learned about Smart Money and I'm genuinely floored",
        "data": "2024-12-24",
        "upvotes": "899",
        "komentarze": "329",
        "opis": "Początkujący trader odkrywa SMC, shock o manipulacji rynku",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "Any thoughts about this strategy",
        "data": "2024-12-07",
        "upvotes": "7",
        "komentarze": "12",
        "opis": "Liquidity Sweep Strategy z SMT Divergence, FVG setups",
        "kod_indykator": "Tak"
    },
    {
        "tytul": "Can a 100% automated trading system be profitable",
        "data": "2024-11-10",
        "upvotes": "23",
        "komentarze": "109",
        "opis": "Dyskusja o automatyzacji tradingu, boty SMC wspominane",
        "kod_indykator": "Tak"
    },
    {
        "tytul": "My Simple, Profitable Day Trading Strategy",
        "data": "2024-12-16",
        "upvotes": "220",
        "komentarze": "67",
        "opis": "Strategia ICT/SMC z 90/30-minute cycles, FVG setups",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "Is SMC the holy grail of trading",
        "data": "2024-11-01",
        "upvotes": "117",
        "komentarze": "127",
        "opis": "GOLD trading z SMC, dyskusja o prematurely closing positions",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "An entry technique to boost your odds",
        "data": "2022-05-05",
        "upvotes": "Brak danych",
        "komentarze": "Średnio",
        "opis": "Breaker technique, break and retest z SMC perspective",
        "kod_indykator": "Nie"
    },
    {
        "tytul": "Do AI-Based Trading Bots Actually Work",
        "data": "2023-10-26",
        "upvotes": "Brak danych",
        "komentarze": "Wysokie",
        "opis": "AI w tradingu, konsensus że boty są nieskuteczne long-term",
        "kod_indykator": "Tak"
    },
    {
        "tytul": "Is smart money trading actually the way we all should trade?",
        "data": "2024-06-09",
        "upvotes": "Brak danych",
        "komentarze": "Średnio",
        "opis": "YouTube traders używają SMC, pytanie czy to właściwy sposób",
        "kod_indykator": "Nie"
    }
]

df_reddit = pd.DataFrame(reddit_posts)
print("\nReddit Posts - SMC Discussion:")
print(df_reddit[['tytul', 'data', 'upvotes', 'komentarze', 'kod_indykator']].to_string(index=False))

# Zliczanie postów z kodem/indykatorami
posts_with_code = df_reddit[df_reddit['kod_indykator'] == 'Tak'].shape[0]
posts_without_code = df_reddit[df_reddit['kod_indykator'] == 'Nie'].shape[0]

print(f"\nStatystyki Reddit:")
print(f"Posty z kodem/indykatorami: {posts_with_code}")
print(f"Posty bez kodu: {posts_without_code}")
print(f"Łącznie przeanalizowanych postów: {len(reddit_posts)}")