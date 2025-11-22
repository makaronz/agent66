import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactElement } from 'react';

// Create a fresh QueryClient for each test
export const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0, // Equivalent to cacheTime in v4
      },
      mutations: {
        retry: false,
      },
    },
  });
};

// Wrapper component for React Query
export const createQueryWrapper = (queryClient?: QueryClient) => {
  const testQueryClient = queryClient || createTestQueryClient();

  return ({ children }: { children: ReactElement }) => (
    <QueryClientProvider client={testQueryClient}>
      {children}
    </QueryClientProvider>
  );
};

// Helper to create successful query response
export const createQueryResponse = <T>(data: T) => ({
  data,
  isLoading: false,
  isError: false,
  isSuccess: true,
  error: null,
  isFetching: false,
  isPlaceholderData: false,
  isFetched: true,
  isFetchedAfterMount: true,
  isRefetching: false,
  isRefetchError: false,
  isRefetching: false,
  status: 'success' as const,
  fetchStatus: 'idle' as const,
});

// Helper to create loading query response
export const createQueryLoading = () => ({
  data: undefined,
  isLoading: true,
  isError: false,
  isSuccess: false,
  error: null,
  isFetching: true,
  isPlaceholderData: false,
  isFetched: false,
  isFetchedAfterMount: false,
  isRefetching: false,
  isRefetchError: false,
  status: 'pending' as const,
  fetchStatus: 'fetching' as const,
});

// Helper to create error query response
export const createQueryError = (error: Error) => ({
  data: undefined,
  isLoading: false,
  isError: true,
  isSuccess: false,
  error,
  isFetching: false,
  isPlaceholderData: false,
  isFetched: true,
  isFetchedAfterMount: true,
  isRefetching: false,
  isRefetchError: false,
  status: 'error' as const,
  fetchStatus: 'idle' as const,
});

// Mock fetch for React Query tests
export const mockFetchResponse = (data: any, ok: boolean = true, status: number = 200) => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok,
      status,
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
      headers: new Headers(),
      redirected: false,
      statusText: ok ? 'OK' : 'Error',
      type: 'basic' as ResponseType,
      url: '',
      clone: jest.fn(),
      body: null,
      bodyUsed: false,
      arrayBuffer: jest.fn(),
      blob: jest.fn(),
      formData: jest.fn(),
    })
  ) as jest.Mock;
};

// Reset all mocks
export const resetMocks = () => {
  jest.clearAllMocks();
  global.fetch = undefined as any;
};