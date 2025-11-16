# 📊 Źródła Danych na Stronie `/trading`

## ⚠️ OBECNY STAN: Używa Mock Data

Strona `/trading` (TradingInterface.tsx) obecnie wyświetla **MOCK DATA** (dane testowe), a nie rzeczywiste dane z systemu.

---

## 🔍 Skąd pochodzą dane?

### 1. **SMC Patterns** (Wykryte wzorce SMC)

**Lokalizacja**: `src/pages/TradingInterface.tsx` linie 14-49

**Obecnie**: Hardcoded `mockSMCPatterns` array
```typescript
const mockSMCPatterns = [
  { id: 1, symbol: 'BTCUSDT', type: 'Order Block', direction: 'Bullish', ... },
  { id: 2, symbol: 'ETHUSDT', type: 'CHoCH', direction: 'Bearish', ... },
  ...
];
```

**Backend endpoint**: `/api/trading/smc-patterns` (linia 138 w `api/routes/trading.ts`)
- ❌ Zwraca również mock data
- ❌ Nie łączy się z Python backend

**Python backend**: 
- ✅ Ma `SMCIndicators` który wykrywa wzorce
- ❌ Brak endpointu API do pobierania wykrytych wzorców

### 2. **Recent Orders** (Ostatnie zlecenia)

**Lokalizacja**: `src/pages/TradingInterface.tsx` linie 51-74

**Obecnie**: Hardcoded `mockOrders` array
```typescript
const mockOrders = [
  { id: 'ORD001', symbol: 'BTCUSDT', side: 'BUY', status: 'FILLED', ... },
  ...
];
```

**Backend endpoint**: Brak dedykowanego endpointu
- ❌ TradingInterface nie wywołuje API dla orders
- ❌ Używa tylko mock data

**Python backend**:
- ✅ Ma `PaperTradingEngine.get_trade_history()` 
- ✅ Endpoint `/api/python/paper-trades` istnieje
- ❌ TradingInterface nie używa tego endpointu

### 3. **Place Order** (Wykonywanie zleceń)

**Lokalizacja**: `src/pages/TradingInterface.tsx` linie 86-97

**Obecnie**: Tylko `console.log` - nie wykonuje rzeczywistego trade
```typescript
const handlePlaceOrder = () => {
  console.log('Placing order:', { symbol, side, type, quantity, ... });
  // TODO: Implement order placement logic
};
```

**Backend endpoint**: `/api/trading/execute-trade` (linia 210)
- ❌ Zwraca mock trade (nie wykonuje rzeczywistego)
- ❌ Nie łączy się z Python backend

**Python backend**:
- ✅ Ma `PaperTradingEngine.execute_order()`
- ❌ Brak endpointu API do manualnego wykonywania trades

---

## 🔧 Co trzeba naprawić

### PRIORITY 1: SMC Patterns - Połączyć z Python Backend

1. **Dodać endpoint w Python backend**:
   - `/api/python/smc-patterns` - zwraca wykryte wzorce SMC
   - Musi przechowywać ostatnie wykryte wzorce w pamięci

2. **Zaktualizować TypeScript backend**:
   - `/api/trading/smc-patterns` powinien pobierać z Python backend
   - Fallback do mock data tylko gdy Python backend niedostępny

3. **Zaktualizować TradingInterface.tsx**:
   - Użyć `apiService.getSMCPatterns()` zamiast `mockSMCPatterns`
   - Dodać `useEffect` do odświeżania wzorców co 30 sekund

### PRIORITY 2: Recent Orders - Połączyć z Paper Trading

1. **Zaktualizować TradingInterface.tsx**:
   - Użyć `apiService.getTradingHistory()` zamiast `mockOrders`
   - Dodać `useEffect` do odświeżania orders co 10 sekund

2. **Backend już ma endpoint**:
   - `/api/trading/history` - ale zwraca mock data
   - Trzeba połączyć z `/api/python/paper-trades`

### PRIORITY 3: Place Order - Wykonywanie rzeczywistych trades

1. **Dodać endpoint w Python backend**:
   - `POST /api/python/execute-order` - wykonuje trade przez PaperTradingEngine
   - Walidacja przez RiskManager
   - Zwraca wynik wykonania

2. **Zaktualizować TypeScript backend**:
   - `/api/trading/execute-trade` powinien przekazywać do Python backend
   - Walidacja danych przed wysłaniem

3. **Zaktualizować TradingInterface.tsx**:
   - `handlePlaceOrder` powinien wywołać `apiService.executeTrade()`
   - Pokazać loading state i wynik wykonania

---

## 📋 Checklist: Przejście na Real Data

- [ ] **SMC Patterns**: Dodać endpoint w Python backend
- [ ] **SMC Patterns**: Połączyć TypeScript backend z Python
- [ ] **SMC Patterns**: Zaktualizować TradingInterface.tsx
- [ ] **Recent Orders**: Połączyć z `/api/python/paper-trades`
- [ ] **Recent Orders**: Zaktualizować TradingInterface.tsx
- [ ] **Place Order**: Dodać endpoint w Python backend
- [ ] **Place Order**: Połączyć TypeScript backend z Python
- [ ] **Place Order**: Zaktualizować TradingInterface.tsx

---

## 🎯 Aktualne Źródła Danych

| Komponent | Obecne Źródło | Docelowe Źródło | Status |
|-----------|---------------|-----------------|--------|
| SMC Patterns | Mock data ❌ | Python SMCIndicators | ❌ Mock |
| Recent Orders | Mock data ❌ | Python PaperTradingEngine | ❌ Mock |
| Place Order | console.log ❌ | Python PaperTradingEngine | ❌ Mock |

---

**Ostatnia aktualizacja**: 2025-11-16

