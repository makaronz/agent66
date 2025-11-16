# ⏱️ Częstotliwość Odświeżania Danych

## 📊 Przegląd Częstotliwości

| Komponent | Częstotliwość | Konfiguracja | Opis |
|-----------|---------------|--------------|------|
| **Frontend Dashboard** | 30 sekund | `src/pages/Dashboard.tsx` | Automatyczne odświeżanie danych rynkowych |
| **Python Trading Agent** | 60 sekund | `start_paper_trading.py` | Główny cykl tradingowy (analiza + decyzje) |
| **Paper Trading Updates** | 60 sekund | `config.yaml` | Aktualizacja pozycji i P&L |
| **Data Pipeline Health** | 30 sekund | `config.yaml` | Health check połączeń WebSocket |
| **WebSocket Data** | Real-time | Binance API | Dane przychodzą natychmiastowo z giełdy |
| **System Health** | 60 sekund | `config.yaml` | Monitoring systemu |

---

## 🔧 Konfiguracja

### 1. Frontend Dashboard (React)

**Lokalizacja**: `src/pages/Dashboard.tsx`

```typescript
// Obecna konfiguracja: 30 sekund
const interval = setInterval(fetchData, 30000);
```

**Zmiana częstotliwości**:
```typescript
// Przykład: 10 sekund
const interval = setInterval(fetchData, 10000);

// Przykład: 60 sekund
const interval = setInterval(fetchData, 60000);
```

### 2. Python Trading Agent

**Lokalizacja**: `start_paper_trading.py`

```python
# Obecna konfiguracja: 60 sekund
for i in range(60):
    if shutdown_flag:
        break
    await asyncio.sleep(1)
```

**Zmiana częstotliwości**:
```python
# Przykład: 30 sekund
for i in range(30):
    await asyncio.sleep(1)

# Przykład: 120 sekund (2 minuty)
for i in range(120):
    await asyncio.sleep(1)
```

### 3. Config.yaml

**Lokalizacja**: `config.yaml`

```yaml
# Paper Trading
paper_trading:
  update_interval: 60  # sekundy

# Data Pipeline
data_pipeline:
  health_check_interval: 30  # sekundy
  performance_log_interval: 60  # sekundy

# Monitoring
monitoring:
  health_check_interval: 60  # sekundy
```

---

## 📈 Rekomendowane Częstotliwości

### Dla Paper Trading (Obecne)
- ✅ **Frontend**: 30s - dobry balans między aktualnością a obciążeniem
- ✅ **Python Agent**: 60s - wystarczające dla SMC patterns (1h timeframe)
- ✅ **WebSocket**: Real-time - maksymalna aktualność danych

### Dla Szybkiego Tradingu (Day Trading)
- ⚡ **Frontend**: 5-10s - częstsze odświeżanie
- ⚡ **Python Agent**: 30s - szybsze decyzje
- ⚡ **Timeframe**: 1m zamiast 1h

### Dla Swing Tradingu (Długoterminowy)
- 🐢 **Frontend**: 60-120s - mniej obciążające
- 🐢 **Python Agent**: 300s (5 min) - rzadsze analizy
- 🐢 **Timeframe**: 4h lub 1d

---

## ⚠️ Uwagi

### Rate Limiting
- **Binance API**: 1200 requestów/minutę
- **Frontend**: 30s = 2 requesty/minutę ✅ (bezpieczne)
- **Python Agent**: 60s = 1 request/minutę ✅ (bezpieczne)

### Obciążenie Systemu
- **Zbyt częste odświeżanie** (>10s frontend) może:
  - Obciążyć backend
  - Zwiększyć zużycie CPU
  - Zwiększyć zużycie sieci

- **Zbyt rzadkie odświeżanie** (>120s) może:
  - Opóźnić wykrycie sygnałów
  - Pokazać nieaktualne dane użytkownikowi

---

## 🔄 WebSocket (Real-time)

WebSocket przesyła dane **natychmiastowo** gdy:
- ✅ Nowa transakcja na giełdzie
- ✅ Zmiana ceny tickera
- ✅ Aktualizacja orderbook

**Nie wymaga konfiguracji** - działa automatycznie.

---

## 📝 Przykłady Zmiany

### Szybkie Odświeżanie (Day Trading)

**1. Frontend** (`src/pages/Dashboard.tsx`):
```typescript
// Zmień z 30000 na 10000 (10 sekund)
const interval = setInterval(fetchData, 10000);
```

**2. Python Agent** (`start_paper_trading.py`):
```python
# Zmień z 60 na 30 (30 sekund)
for i in range(30):
    await asyncio.sleep(1)
```

**3. Config** (`config.yaml`):
```yaml
paper_trading:
  update_interval: 30  # 30 sekund
```

### Wolne Odświeżanie (Swing Trading)

**1. Frontend**:
```typescript
// Zmień na 60000 (60 sekund)
const interval = setInterval(fetchData, 60000);
```

**2. Python Agent**:
```python
// Zmień na 300 (5 minut)
for i in range(300):
    await asyncio.sleep(1)
```

**3. Config**:
```yaml
paper_trading:
  update_interval: 300  # 5 minut
```

---

## 🎯 Aktualne Ustawienia (Domyślne)

```
Frontend Dashboard:     30 sekund
Python Trading Agent:  60 sekund
Paper Trading Updates: 60 sekund
Data Pipeline Health:  30 sekund
System Health:         60 sekund
WebSocket:             Real-time (natychmiastowo)
```

---

## 💡 Wskazówki

1. **Dla większości przypadków**: Obecne ustawienia (30s/60s) są optymalne
2. **Dla testowania**: Możesz zmniejszyć do 10s/30s aby szybciej zobaczyć wyniki
3. **Dla produkcji**: Zwiększ do 60s/120s aby zmniejszyć obciążenie
4. **WebSocket**: Zawsze pozostaw real-time - to nie obciąża systemu

---

## 🔍 Sprawdzenie Aktualnych Ustawień

```bash
# Sprawdź częstotliwość w kodzie
grep -r "setInterval\|sleep\|interval" src/ start_paper_trading.py config.yaml
```

---

**Ostatnia aktualizacja**: 2025-11-16

