# Iteration 2 Implementation Plan: "Order in the Orchestra"

## Overview

This iteration focuses on implementing proper state management architecture using Zustand and TanStack Query to replace the current chaotic state management and create a scalable, maintainable foundation.

## Goals

* Replace React Context chaos with Zustand global state

* Implement TanStack Query for server state management

* Separate concerns between Auth and Market Data

* Create proper error boundaries and loading states

* Add offline mode capabilities

* Establish clean TypeScript interfaces

## Implementation Steps

### Phase 1: Dependencies and Setup

#### 1.1 Install Required Dependencies

```bash
cd /Users/arkadiuszfudali/Git/agent66/smc_trading_agent
pnpm add @tanstack/react-query zustand immer
pnpm add -D @tanstack/react-query-devtools
```

#### 1.2 Create Base Store Structure

**File:** **`src/stores/index.ts`**

* Export all store slices

* Configure store composition

### Phase 2: Zustand Store Implementation

#### 2.1 Auth Store

**File:** **`src/stores/authStore.ts`**

* User authentication state

* Session management

* Profile data

* Auth actions (login, logout, refresh)

#### 2.2 Market Data Store

**File:** **`src/stores/marketDataStore.ts`**

* Real-time market data state

* Symbol subscriptions

* Connection status

* WebSocket management actions

#### 2.3 UI Store

**File:** **`src/stores/uiStore.ts`**

* Loading states

* Error messages

* Offline mode status

* Toast notifications

#### 2.4 Chart Store

**File:** **`src/stores/chartStore.ts`**

* Chart configuration

* Selected timeframes

* Chart data cache

* Drawing tools state

### Phase 3: TanStack Query Setup

#### 3.1 Query Client Configuration

**File:** **`src/lib/queryClient.ts`**

* Configure React Query client

* Set default options

* Error handling

* Offline support

#### 3.2 Query Keys Factory

**File:** **`src/lib/queryKeys.ts`**

* Centralized query key management

* Type-safe query keys

* Hierarchical key structure

#### 3.3 Query Hooks

**File:** **`src/hooks/queries/`**

* `useMarketDataQuery.ts` - Market data fetching

* `useExchangeInfoQuery.ts` - Exchange information

* `useOrderBookQuery.ts` - Order book data

* `useTickerQuery.ts` - Ticker data

### Phase 4: Context Refactoring

#### 4.1 Simplified Auth Context

**File:** **`src/contexts/AuthContext.tsx`** **(Refactor)**

* Remove market data concerns

* Focus only on Supabase auth

* Integrate with auth store

* Simplified provider

#### 4.2 Chart Data Context

**File:** **`src/contexts/ChartContext.tsx`** **(New)**

* Chart-specific data management

* Integration with chart store

* Real-time data subscriptions

#### 4.3 Query Provider Setup

**File:** **`src/providers/QueryProvider.tsx`** **(New)**

* TanStack Query provider

* DevTools integration

* Error boundaries

### Phase 5: Hook Refactoring

#### 5.1 Market Data Hook

**File:** **`src/hooks/useMarketData.ts`** **(Refactor)**

* Remove direct API calls

* Use Zustand store

* Integrate with TanStack Query

* Simplified interface

#### 5.2 WebSocket Hook

**File:** **`src/hooks/useWebSocket.ts`** **(New)**

* Dedicated WebSocket management

* Connection state handling

* Automatic reconnection

* Store integration

#### 5.3 Offline Hook

**File:** **`src/hooks/useOffline.ts`** **(New)**

* Network status detection

* Offline mode management

* Cache fallback logic

### Phase 6: Error Boundaries and Loading States

#### 6.1 Enhanced Error Boundary

**File:** **`src/components/ErrorBoundary.tsx`** **(Enhance)**

* Better error reporting

* Recovery mechanisms

* User-friendly error messages

#### 6.2 Loading Components

**File:** **`src/components/Loading/`**

* `LoadingSpinner.tsx` - Generic spinner

* `ChartLoading.tsx` - Chart-specific loading

* `DataLoading.tsx` - Data loading states

#### 6.3 Suspense Boundaries

**File:** **`src/components/SuspenseBoundary.tsx`** **(New)**

* Proper suspense handling

* Fallback components

* Error recovery

### Phase 7: TypeScript Interfaces

#### 7.1 Store Types

**File:** **`src/types/stores.ts`** **(New)**

* Auth store interfaces

* Market data store interfaces

* UI store interfaces

* Chart store interfaces

#### 7.2 Query Types

**File:** **`src/types/queries.ts`** **(New)**

* Query response types

* Query options types

* Error types

#### 7.3 Enhanced API Types

**File:** **`src/types/api.ts`** **(Enhance)**

* Improved Binance API types

* WebSocket message types

* Error response types

### Phase 8: Component Updates

#### 8.1 Dashboard Component

**File:** **`src/components/Dashboard.tsx`** **(Refactor)**

* Use new store hooks

* Implement proper loading states

* Error handling

#### 8.2 Chart Component

**File:** **`src/components/Chart/`** **(Refactor)**

* Integration with chart store

* Real-time data updates

* Offline mode support

#### 8.3 Market Data Components

**File:** **`src/components/MarketData/`** **(Refactor)**

* Use query hooks

* Proper error boundaries

* Loading states

### Phase 9: App Structure Updates

#### 9.1 Main App File

**File:** **`src/App.tsx`** **(Refactor)**

* Add Query Provider

* Update provider hierarchy

* Add error boundaries

#### 9.2 Root Component

**File:** **`src/main.tsx`** **(Update)**

* Query client setup

* DevTools integration

## File Modification Summary

### New Files to Create:

* `src/stores/index.ts`

* `src/stores/authStore.ts`

* `src/stores/marketDataStore.ts`

* `src/stores/uiStore.ts`

* `src/stores/chartStore.ts`

* `src/lib/queryClient.ts`

* `src/lib/queryKeys.ts`

* `src/hooks/queries/useMarketDataQuery.ts`

* `src/hooks/queries/useExchangeInfoQuery.ts`

* `src/hooks/queries/useOrderBookQuery.ts`

* `src/hooks/queries/useTickerQuery.ts`

* `src/contexts/ChartContext.tsx`

* `src/providers/QueryProvider.tsx`

* `src/hooks/useWebSocket.ts`

* `src/hooks/useOffline.ts`

* `src/components/Loading/LoadingSpinner.tsx`

* `src/components/Loading/ChartLoading.tsx`

* `src/components/Loading/DataLoading.tsx`

* `src/components/SuspenseBoundary.tsx`

* `src/types/stores.ts`

* `src/types/queries.ts`

### Files to Modify:

* `src/contexts/AuthContext.tsx` - Simplify and integrate with store

* `src/hooks/useMarketData.ts` - Refactor to use new architecture

* `src/components/ErrorBoundary.tsx` - Enhance error handling

* `src/types/api.ts` - Add new types

* `src/components/Dashboard.tsx` - Update to use new hooks

* `src/components/Chart/` - Refactor for new architecture

* `src/components/MarketData/` - Update to use queries

* `src/App.tsx` - Add new providers

* `src/main.tsx` - Setup query client

## Implementation Order

1. **Dependencies Installation** (5 minutes)
2. **Store Setup** (30 minutes)

   * Create base store structure

   * Implement auth store

   * Implement market data store
3. **Query Client Setup** (20 minutes)

   * Configure TanStack Query

   * Setup query keys
4. **Context Refactoring** (25 minutes)

   * Simplify AuthContext

   * Create ChartContext
5. **Hook Implementation** (40 minutes)

   * Refactor useMarketData

   * Create query hooks

   * Add WebSocket hook
6. **Component Updates** (30 minutes)

   * Update Dashboard

   * Add loading components

   * Enhance error boundaries
7. **App Integration** (20 minutes)

   * Update App.tsx

   * Setup providers
8. **Testing & Validation** (30 minutes)

   * Test all functionality

   * Verify error handling

   * Check offline mode

**Total Estimated Time: 3.5 hours**

## Benefits After Implementation

* **Predictable State Management**: Zustand provides clear, type-safe state updates

* **Efficient Server State**: TanStack Query handles caching, background updates, and error recovery

* **Better Performance**: Reduced re-renders and optimized data fetching

* **Improved Developer Experience**: Better debugging with DevTools

* **Offline Support**: Graceful degradation when network is unavailable

* **Scalability**: Clean architecture that can grow with the application

* **Type Safety**: Comprehensive TypeScript coverage

* **Error Resilience**: Proper error boundaries and recovery mechanisms

## Risk Mitigation

* **Gradual Migration**: Implement stores alongside existing context initially

* **Backward Compatibility**: Keep existing APIs during transition

* **Comprehensive Testing**: Test each component after migration

* **Rollback Plan**: Keep original implementations until fully validated

* **Performance Monitoring**: Watch for any performance regressions

## Next Steps (Iteration 3)

After successful implementation of Iteration 2, we'll be ready for Iteration 3: "Production Armor" which will include:

* Advanced rate limiting with token bucket

* Sophisticated retry mechanisms with jitter

* Comprehensive monitoring and analytics

* Advanced offline capabilities

* Performance optimizations

* Security hardening

