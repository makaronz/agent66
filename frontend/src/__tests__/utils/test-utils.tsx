import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { configureStore } from '@reduxjs/toolkit';
import { Toaster } from 'react-hot-toast';
import { store } from '../../store/store';

// Custom test wrapper with all providers
const AllTheProviders = ({
  children,
  initialState = {},
  queryClient
}: {
  children: React.ReactNode;
  initialState?: any;
  queryClient?: QueryClient;
}) => {
  const testQueryClient = queryClient || new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const testStore = configureStore({
    reducer: {
      auth: (state = { ...initialState.auth, token: null, isAuthenticated: false, loading: false, user: null, error: null }) => state,
      posts: (state = initialState.posts || {}) => state,
    },
    preloadedState: initialState,
  });

  return (
    <Provider store={testStore}>
      <QueryClientProvider client={testQueryClient}>
        <BrowserRouter>
          {children}
          <Toaster />
        </BrowserRouter>
      </QueryClientProvider>
    </Provider>
  );
};

// Custom render function with providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & {
    initialState?: any;
    queryClient?: QueryClient;
  }
) => {
  const { initialState, queryClient, ...renderOptions } = options || {};

  return render(ui, {
    wrapper: ({ children }) => (
      <AllTheProviders initialState={initialState} queryClient={queryClient}>
        {children}
      </AllTheProviders>
    ),
    ...renderOptions,
  });
};

// Mock window.matchMedia for responsive testing
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver for components that use it
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock ResizeObserver for responsive components
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Re-export everything from testing-library
export * from '@testing-library/react';
export { customRender as render };
export { AllTheProviders };