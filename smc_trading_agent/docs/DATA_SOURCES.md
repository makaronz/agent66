# 📊 Źródła Danych w Dashboard

## ⚠️ OBECNY STAN: Używa Mock Data

Dashboard obecnie wyświetla **MOCK DATA** (dane testowe), a nie rzeczywiste dane z Python trading agenta.

---

## 🔍 Skąd pochodzą dane?

### 1. **Positions (Pozycje)** - `/api/trading/positions`

**Obecnie**: Mock data z `api/routes/trading.ts`
```typescript
const mockPositions = [
  { symbol: 'BTCUSDT', side: 'LONG', size: 0.5, entryPrice: 42800, ... },
  { symbol: 'ETHUSDT', side: 'SHORT', size: 2.0, entryPrice: 2680, ... },
];
```

**Powinno być**: Dane z Python backend (`/api/python/positions`)
- ✅ Endpoint istnieje w `api/routes/trading.ts` (linia 560)
- ❌ Ale używa fallback do `mockPositions` gdy Python backend nie odpowiada

### 2. **Performance Metrics** - `/api/trading/performance`

**Obecnie**: Mock data (hardcoded)
```typescript
const mockMetrics = {
  totalPnL: 283.75,
  sharpeRatio: 1.67,
  maxDrawdown: -3.2,
  winRate: 68.5,
  ...
};
```

**Powinno być**: Obliczone z rzeczywistych transakcji z Python backend

### 3. **Market Data** - `/api/trading/market-data`

**Status**: ✅ **DZIAŁA** - Pobiera z Binance WebSocket (real-time)
- Używa `MarketDataAggregator`
- Fallback do mock data tylko gdy aggregator nie zainicjalizowany

---

## 🔧 Jak naprawić - Połączyć z Python Backend

### Problem 1: Positions endpoint używa mocków

**Lokalizacja**: `api/routes/trading.ts` linia 500-560

**Obecny kod**:
```typescript
router.get('/positions', async (req: Request, res: Response) => {
  // ... próbuje pobrać z marketDataAggregator
  // ... ale używa mockPositions jako fallback
});
```

**Rozwiązanie**: Zmienić aby zawsze próbował Python backend:
```typescript
router.get('/positions', async (req: Request, res: Response) => {
  try {
    // Najpierw spróbuj Python backend
    const response = await fetch('http://localhost:8000/api/python/positions');
    if (response.ok) {
      const data = await response.json();
      return res.json(data); // Zwróć rzeczywiste dane
    }
  } catch (error) {
    console.error('Python backend unavailable, using fallback');
  }
  
  // Fallback tylko gdy Python backend nie działa
  return res.json({ ...mockPositions });
});
```

### Problem 2: Performance metrics są hardcoded

**Lokalizacja**: `api/routes/trading.ts` linia 243-263

**Rozwiązanie**: Obliczyć z Python backend:
```typescript
router.get('/performance', async (req: Request, res: Response) => {
  try {
    // Pobierz wszystkie trades z Python backend
    const tradesRes = await fetch('http://localhost:8000/api/python/paper-trades?limit=1000');
    const tradesData = await tradesRes.json();
    
    if (tradesData.success && tradesData.data) {
      // Oblicz metryki z rzeczywistych transakcji
      const metrics = calculatePerformanceMetrics(tradesData.data);
      return res.json({ success: true, data: metrics });
    }
  } catch (error) {
    console.error('Failed to get performance from Python backend');
  }
  
  // Fallback
  return res.json({ success: true, data: mockMetrics });
});
```

---

## 📋 Checklist: Przejście na Real Data

- [ ] **Positions**: Połączyć z `/api/python/positions`
- [ ] **Performance**: Obliczyć z `/api/python/paper-trades`
- [ ] **Account Summary**: Użyć `/api/python/account`
- [ ] **Market Data**: ✅ Już działa (Binance WebSocket)
- [ ] **System Health**: Można dodać real health checks

---

## 🎯 Aktualne Źródła Danych

| Endpoint | Obecne Źródło | Docelowe Źródło | Status |
|----------|---------------|-----------------|--------|
| `/market-data` | Binance WebSocket ✅ | Binance WebSocket ✅ | ✅ Real |
| `/positions` | Mock data ❌ | Python backend | ❌ Mock |
| `/performance` | Mock data ❌ | Python backend | ❌ Mock |
| `/paper-trades` | Python backend ✅ | Python backend ✅ | ✅ Real |
| `/account-summary` | Python backend ✅ | Python backend ✅ | ✅ Real |
| `/system-health` | Mock data ❌ | Real health checks | ❌ Mock |

---

## 💡 Dlaczego widzisz te dane?

**Total P&L $24900.73** - To jest **mock data** z backendu TypeScript, nie rzeczywiste P&L z paper trading engine.

**BTCUSDT LONG $25749.05** - To jest **mock position** z `mockPositions` array, nie rzeczywista pozycja z Python backend.

**Sharpe Ratio 1.67, Win Rate 68.5%** - To są **hardcoded wartości** w `mockMetrics`, nie obliczone z rzeczywistych transakcji.

---

## 🚀 Następne kroki

1. **Sprawdź czy Python backend działa**: `curl http://localhost:8000/api/python/positions`
2. **Sprawdź czy TypeScript backend łączy się z Python**: Sprawdź logi
3. **Napraw endpoints** aby używały Python backend zamiast mocków
4. **Przetestuj** - Dashboard powinien pokazywać rzeczywiste dane z paper trading

---

**Ostatnia aktualizacja**: 2025-11-16

