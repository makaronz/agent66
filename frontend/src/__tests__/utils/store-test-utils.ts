import { configureStore } from '@reduxjs/toolkit';
import { AnyAction } from '@reduxjs/toolkit';
import { ThunkDispatch } from 'redux-thunk';
import authReducer, {
  loginUser,
  registerUser,
  logout,
  AuthState
} from '../../store/slices/authSlice';
import postReducer from '../../store/slices/postSlice';

export type RootState = {
  auth: AuthState;
  posts: any;
};

export type AppDispatch = ThunkDispatch<RootState, any, AnyAction>;

// Create a test store with initial state
export const createTestStore = (initialState?: Partial<RootState>) => {
  return configureStore({
    reducer: {
      auth: authReducer,
      posts: postReducer,
    },
    preloadedState: {
      auth: {
        token: null,
        isAuthenticated: false,
        loading: false,
        user: null,
        error: null,
        ...initialState?.auth,
      },
      posts: {
        posts: [],
        loading: false,
        error: null,
        ...initialState?.posts,
      },
    },
  });
};

// Mock user data for testing
export const mockUser = {
  id: '1',
  email: 'test@example.com',
  name: 'Test User',
  firstName: 'Test',
  lastName: 'User',
};

// Mock authentication token
export const mockToken = 'mock-jwt-token-123';

// Mock login credentials
export const mockLoginCredentials = {
  email: 'test@example.com',
  password: 'password123',
};

// Mock registration data
export const mockRegisterData = {
  name: 'Test User',
  email: 'test@example.com',
  password: 'password123',
  confirmPassword: 'password123',
};

// Helper to test async thunks
export const testAsyncThunk = async (
  thunk: any,
  payload: any,
  initialState?: Partial<RootState>
) => {
  const store = createTestStore(initialState);
  const result = await store.dispatch(thunk(payload));
  const state = store.getState();

  return { store, result, state };
};

// Mock axios for API calls
export const mockAxiosSuccess = (data: any) => {
  return Promise.resolve({
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: {} as any,
  });
};

export const mockAxiosError = (message: string, status: number = 400) => {
  const error: any = new Error(message);
  error.response = {
    status,
    data: { message },
    statusText: 'Bad Request',
    headers: {},
    config: {} as any,
  };
  return Promise.reject(error);
};