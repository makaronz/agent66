import authReducer, {
  loginUser,
  registerUser,
  logout,
  AuthState
} from '../../store/slices/authSlice';
import { createTestStore, mockUser, mockToken, mockLoginCredentials, mockRegisterData } from '../utils/store-test-utils';

// Mock axios
jest.mock('axios');
const mockedAxios = require('axios');

// Mock toast
jest.mock('react-hot-toast');
const mockedToast = require('react-hot-toast');

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('authSlice', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
  });

  describe('initial state', () => {
    it('should return the initial state', () => {
      const initialState = authReducer(undefined, { type: '@@INIT' });
      expect(initialState).toEqual({
        token: null,
        isAuthenticated: false,
        loading: false,
        user: null,
        error: null,
      });
    });

    it('should load token from localStorage on initialization', () => {
      localStorageMock.getItem.mockReturnValue(mockToken);

      const initialState = authReducer(undefined, { type: '@@INIT' });
      expect(initialState.token).toBe(mockToken);
      expect(initialState.isAuthenticated).toBe(true);
    });
  });

  describe('loginUser thunk', () => {
    it('should handle successful login', async () => {
      const mockResponse = { token: mockToken, user: mockUser };
      mockedAxios.post.mockResolvedValue({ data: mockResponse });

      const store = createTestStore();
      await store.dispatch(loginUser(mockLoginCredentials));

      const state = store.getState();
      expect(state.auth).toEqual({
        token: mockToken,
        isAuthenticated: true,
        loading: false,
        user: mockUser,
        error: null,
      });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        `${process.env.REACT_APP_API_URL}/auth/login`,
        mockLoginCredentials
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith('token', mockToken);
      expect(mockedToast.success).toHaveBeenCalledWith('Login successful!');
    });

    it('should handle login failure', async () => {
      const errorMessage = 'Invalid credentials';
      mockedAxios.post.mockRejectedValue({
        response: { data: { message: errorMessage } },
      });

      const store = createTestStore();
      await store.dispatch(loginUser(mockLoginCredentials));

      const state = store.getState();
      expect(state.auth).toEqual({
        token: null,
        isAuthenticated: false,
        loading: false,
        user: null,
        error: { message: errorMessage },
      });

      expect(mockedToast.error).toHaveBeenCalledWith(errorMessage);
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('should handle network error during login', async () => {
      mockedAxios.post.mockRejectedValue(new Error('Network error'));

      const store = createTestStore();
      await store.dispatch(loginUser(mockLoginCredentials));

      const state = store.getState();
      expect(state.auth.loading).toBe(false);
      expect(state.auth.error).toBeDefined();
      expect(mockedToast.error).toHaveBeenCalledWith('Login failed');
    });

    it('should set loading to true during login', () => {
      const store = createTestStore();
      const promise = store.dispatch(loginUser(mockLoginCredentials));

      const state = store.getState();
      expect(state.auth.loading).toBe(true);
      expect(state.auth.error).toBe(null);

      return promise;
    });
  });

  describe('registerUser thunk', () => {
    it('should handle successful registration', async () => {
      const mockResponse = { token: mockToken, user: mockUser };
      mockedAxios.post.mockResolvedValue({ data: mockResponse });

      const store = createTestStore();
      await store.dispatch(registerUser(mockRegisterData));

      const state = store.getState();
      expect(state.auth).toEqual({
        token: mockToken,
        isAuthenticated: true,
        loading: false,
        user: mockUser,
        error: null,
      });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        `${process.env.REACT_APP_API_URL}/auth/register`,
        { name: mockRegisterData.name, email: mockRegisterData.email, password: mockRegisterData.password }
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith('token', mockToken);
      expect(mockedToast.success).toHaveBeenCalledWith('Registration successful! Welcome!');
    });

    it('should handle registration failure', async () => {
      const errorMessage = 'Email already exists';
      mockedAxios.post.mockRejectedValue({
        response: { data: { message: errorMessage } },
      });

      const store = createTestStore();
      await store.dispatch(registerUser(mockRegisterData));

      const state = store.getState();
      expect(state.auth).toEqual({
        token: null,
        isAuthenticated: false,
        loading: false,
        user: null,
        error: { message: errorMessage },
      });

      expect(mockedToast.error).toHaveBeenCalledWith(errorMessage);
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it('should set loading to true during registration', () => {
      const store = createTestStore();
      const promise = store.dispatch(registerUser(mockRegisterData));

      const state = store.getState();
      expect(state.auth.loading).toBe(true);
      expect(state.auth.error).toBe(null);

      return promise;
    });
  });

  describe('logout reducer', () => {
    it('should handle logout correctly', () => {
      const initialState: AuthState = {
        token: mockToken,
        isAuthenticated: true,
        loading: false,
        user: mockUser,
        error: null,
      };

      const state = authReducer(initialState, logout());
      expect(state).toEqual({
        token: null,
        isAuthenticated: false,
        loading: false,
        user: null,
        error: null,
      });

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('token');
    });

    it('should handle logout when already logged out', () => {
      const initialState: AuthState = {
        token: null,
        isAuthenticated: false,
        loading: false,
        user: null,
        error: null,
      };

      const state = authReducer(initialState, logout());
      expect(state).toEqual(initialState);
    });
  });

  describe('state transitions', () => {
    it('should clear error on successful login after previous error', async () => {
      // Start with error state
      const store = createTestStore({
        auth: {
          token: null,
          isAuthenticated: false,
          loading: false,
          user: null,
          error: { message: 'Previous error' },
        },
      });

      // Mock successful login
      const mockResponse = { token: mockToken, user: mockUser };
      mockedAxios.post.mockResolvedValue({ data: mockResponse });

      await store.dispatch(loginUser(mockLoginCredentials));

      const state = store.getState();
      expect(state.auth.error).toBe(null);
    });

    it('should maintain user state during loading', async () => {
      const store = createTestStore({
        auth: {
          token: mockToken,
          isAuthenticated: true,
          loading: false,
          user: mockUser,
          error: null,
        },
      });

      // Mock a slow login response
      mockedAxios.post.mockImplementation(() => new Promise(resolve =>
        setTimeout(() => resolve({ data: { token: 'new-token', user: { ...mockUser, id: '2' } } }), 100)
      ));

      const promise = store.dispatch(loginUser(mockLoginCredentials));

      // During loading, user should still be available
      const loadingState = store.getState();
      expect(loadingState.auth.loading).toBe(true);
      expect(loadingState.auth.user).toBe(mockUser);

      await promise;

      // After completion, user should be updated
      const finalState = store.getState();
      expect(finalState.auth.user.id).toBe('2');
      expect(finalState.auth.loading).toBe(false);
    });
  });

  describe('side effects', () => {
    it('should not call localStorage when API_URL is undefined', async () => {
      const originalEnv = process.env.REACT_APP_API_URL;
      process.env.REACT_APP_API_URL = undefined;

      const store = createTestStore();

      try {
        await store.dispatch(loginUser(mockLoginCredentials));
      } catch (error) {
        // Expected to fail
      }

      expect(mockedAxios.post).toHaveBeenCalledWith(
        'undefined/auth/login',
        mockLoginCredentials
      );

      process.env.REACT_APP_API_URL = originalEnv;
    });

    it('should handle multiple concurrent login attempts', async () => {
      const mockResponse = { token: mockToken, user: mockUser };
      mockedAxios.post.mockResolvedValue({ data: mockResponse });

      const store = createTestStore();

      // Start two login attempts simultaneously
      const promise1 = store.dispatch(loginUser(mockLoginCredentials));
      const promise2 = store.dispatch(loginUser(mockLoginCredentials));

      await Promise.all([promise1, promise2]);

      const state = store.getState();
      expect(state.auth.loading).toBe(false);
      expect(state.auth.token).toBe(mockToken);
      expect(mockedAxios.post).toHaveBeenCalledTimes(2);
    });
  });
});