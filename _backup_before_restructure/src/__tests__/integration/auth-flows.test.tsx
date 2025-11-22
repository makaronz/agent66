import React from 'react';
import { screen, fireEvent, waitFor } from '../utils/test-utils';
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { store } from '../../store/store';
import App from '../../App';
import { loginUser, registerUser } from '../../store/slices/authSlice';
import { mockLoginCredentials, mockRegisterData, mockUser, mockToken } from '../utils/store-test-utils';

// Mock the auth slice
jest.mock('../../store/slices/authSlice');
const mockLoginUser = loginUser as jest.MockedFunction<typeof loginUser>;
const mockRegisterUser = registerUser as jest.MockedFunction<typeof registerUser>;

// Mock fetch for dashboard calls
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ crew: { total: 0, active: 0 }, projects: { active: 0 }, recentActivity: [] }),
    headers: new Headers(),
    redirected: false,
    statusText: 'OK',
    type: 'basic' as ResponseType,
    url: '',
    clone: jest.fn(),
    body: null,
    bodyUsed: false,
    arrayBuffer: jest.fn(),
    blob: jest.fn(),
    formData: jest.fn(),
    text: () => Promise.resolve('{}'),
  })
) as jest.Mock;

describe('Authentication Integration Tests', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    jest.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const renderApp = () => {
    return render(
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </Provider>
    );
  };

  describe('Registration Flow', () => {
    it('should complete full registration flow successfully', async () => {
      // Mock successful registration
      mockRegisterUser.mockResolvedValue({
        type: 'auth/register/fulfilled',
        payload: { token: mockToken, user: mockUser },
      } as any);

      renderApp();

      // Navigate to registration
      const registerLink = screen.getByRole('link', { name: /register here/i });
      fireEvent.click(registerLink);

      // Fill registration form
      const nameInput = screen.getByLabelText(/name/i);
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);

      fireEvent.change(nameInput, { target: { value: mockRegisterData.name } });
      fireEvent.change(emailInput, { target: { value: mockRegisterData.email } });
      fireEvent.change(passwordInput, { target: { value: mockRegisterData.password } });
      fireEvent.change(confirmPasswordInput, { target: { value: mockRegisterData.confirmPassword } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /register/i });
      fireEvent.click(submitButton);

      // Wait for registration to complete and redirect
      await waitFor(() => {
        expect(mockRegisterUser).toHaveBeenCalledWith({
          name: mockRegisterData.name,
          email: mockRegisterData.email,
          password: mockRegisterData.password,
        });
      });

      // Should be redirected to dashboard
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
      });
    });

    it('should show validation errors for invalid registration data', async () => {
      renderApp();

      // Navigate to registration
      const registerLink = screen.getByRole('link', { name: /register here/i });
      fireEvent.click(registerLink);

      // Submit empty form
      const submitButton = screen.getByRole('button', { name: /register/i });
      fireEvent.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/name must be at least 2 characters long/i)).toBeInTheDocument();
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument();
        expect(screen.getByText(/password must be at least 6 characters long/i)).toBeInTheDocument();
      });
    });

    it('should handle registration failure', async () => {
      // Mock failed registration
      mockRegisterUser.mockResolvedValue({
        type: 'auth/register/rejected',
        payload: 'Email already exists',
      } as any);

      renderApp();

      // Navigate to registration and fill form
      const registerLink = screen.getByRole('link', { name: /register here/i });
      fireEvent.click(registerLink);

      const nameInput = screen.getByLabelText(/name/i);
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/^password/i);
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);

      fireEvent.change(nameInput, { target: { value: mockRegisterData.name } });
      fireEvent.change(emailInput, { target: { value: mockRegisterData.email } });
      fireEvent.change(passwordInput, { target: { value: mockRegisterData.password } });
      fireEvent.change(confirmPasswordInput, { target: { value: mockRegisterData.confirmPassword } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /register/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockRegisterUser).toHaveBeenCalled();
      });

      // Should stay on registration page
      expect(screen.getByRole('heading', { name: /register/i })).toBeInTheDocument();
    });
  });

  describe('Login Flow', () => {
    it('should complete full login flow successfully', async () => {
      // Mock successful login
      mockLoginUser.mockResolvedValue({
        type: 'auth/login/fulfilled',
        payload: { token: mockToken, user: mockUser },
      } as any);

      renderApp();

      // Should be on login page by default
      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();

      // Fill login form
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);

      fireEvent.change(emailInput, { target: { value: mockLoginCredentials.email } });
      fireEvent.change(passwordInput, { target: { value: mockLoginCredentials.password } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /login/i });
      fireEvent.click(submitButton);

      // Wait for login to complete
      await waitFor(() => {
        expect(mockLoginUser).toHaveBeenCalledWith(mockLoginCredentials);
      });

      // Should be redirected to dashboard
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
      });
    });

    it('should handle login failure', async () => {
      // Mock failed login
      mockLoginUser.mockResolvedValue({
        type: 'auth/login/rejected',
        payload: 'Invalid credentials',
      } as any);

      renderApp();

      // Fill login form with wrong credentials
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);

      fireEvent.change(emailInput, { target: { value: 'wrong@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /login/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockLoginUser).toHaveBeenCalled();
      });

      // Should stay on login page
      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    });

    it('should show validation errors for invalid login data', async () => {
      renderApp();

      // Submit empty form
      const submitButton = screen.getByRole('button', { name: /login/i });
      fireEvent.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument();
        expect(screen.getByText(/password must be at least 6 characters long/i)).toBeInTheDocument();
      });
    });
  });

  describe('Navigation Flow', () => {
    it('should navigate between login and registration pages', () => {
      renderApp();

      // Should start on login page
      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();

      // Navigate to registration
      const registerLink = screen.getByRole('link', { name: /register here/i });
      fireEvent.click(registerLink);

      // Should be on registration page
      expect(screen.getByRole('heading', { name: /register/i })).toBeInTheDocument();

      // Navigate back to login
      const loginLink = screen.getByRole('link', { name: /login here/i });
      fireEvent.click(loginLink);

      // Should be back on login page
      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    });
  });

  describe('Protected Routes', () => {
    it('should redirect to login when accessing protected routes without authentication', () => {
      renderApp();

      // Try to access dashboard directly
      window.history.pushState({}, 'Dashboard', '/');

      // Should redirect to login page
      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: /dashboard/i })).not.toBeInTheDocument();
    });

    it('should allow access to protected routes after authentication', async () => {
      // Mock successful login
      mockLoginUser.mockResolvedValue({
        type: 'auth/login/fulfilled',
        payload: { token: mockToken, user: mockUser },
      } as any);

      renderApp();

      // Login first
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);

      fireEvent.change(emailInput, { target: { value: mockLoginCredentials.email } });
      fireEvent.change(passwordInput, { target: { value: mockLoginCredentials.password } });

      const submitButton = screen.getByRole('button', { name: /login/i });
      fireEvent.click(submitButton);

      // Should be able to access dashboard
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
      });

      // Should be able to navigate to other protected routes
      const projectsLink = screen.getByRole('link', { name: /projects/i });
      expect(projectsLink).toBeInTheDocument();

      const crewLink = screen.getByRole('link', { name: /crew/i });
      expect(crewLink).toBeInTheDocument();

      const reportsLink = screen.getByRole('link', { name: /reports/i });
      expect(reportsLink).toBeInTheDocument();
    });
  });

  describe('Form Interaction and State Management', () => {
    it('should maintain form state during navigation', () => {
      renderApp();

      // Fill login form partially
      const emailInput = screen.getByLabelText(/email/i);
      fireEvent.change(emailInput, { target: { value: mockLoginCredentials.email } });

      // Navigate to registration
      const registerLink = screen.getByRole('link', { name: /register here/i });
      fireEvent.click(registerLink);

      // Navigate back to login
      const loginLink = screen.getByRole('link', { name: /login here/i });
      fireEvent.click(loginLink);

      // Form should be reset (new component instance)
      expect(emailInput).toHaveValue('');
    });

    it('should handle rapid form submissions', async () => {
      mockLoginUser.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

      renderApp();

      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /login/i });

      fireEvent.change(emailInput, { target: { value: mockLoginCredentials.email } });
      fireEvent.change(passwordInput, { target: { value: mockLoginCredentials.password } });

      // Submit twice quickly
      fireEvent.click(submitButton);
      fireEvent.click(submitButton);

      // Button should be disabled during loading
      expect(submitButton).toBeDisabled();

      // Should only call login once
      await waitFor(() => {
        expect(mockLoginUser).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      mockLoginUser.mockRejectedValue(new Error('Network error'));

      renderApp();

      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /login/i });

      fireEvent.change(emailInput, { target: { value: mockLoginCredentials.email } });
      fireEvent.change(passwordInput, { target: { value: mockLoginCredentials.password } });

      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockLoginUser).toHaveBeenCalled();
      });

      // Should stay on login page
      expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();

      // Button should be enabled again
      expect(submitButton).toBeEnabled();
    });

    it('should handle form validation errors properly', async () => {
      renderApp();

      const emailInput = screen.getByLabelText(/email/i);
      const submitButton = screen.getByRole('button', { name: /login/i });

      // Enter invalid email
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument();
        expect(emailInput).toHaveClass('border-red-500');
      });

      // Should not submit the form
      expect(mockLoginUser).not.toHaveBeenCalled();
    });
  });
});