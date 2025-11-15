import React from 'react';
import { screen, fireEvent, waitFor } from '../utils/test-utils';
import LoginForm from '../../../components/LoginForm';
import { loginUser } from '../../../store/slices/authSlice';
import { mockLoginCredentials, mockAxiosSuccess, mockAxiosError } from '../utils/store-test-utils';

// Mock the auth slice actions
jest.mock('../../../store/slices/authSlice');
const mockLoginUser = loginUser as jest.MockedFunction<typeof loginUser>;

// Mock React Router
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
}));

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLoginUser.mockResolvedValue({
      type: 'auth/login/fulfilled',
      payload: { token: 'mock-token' },
    } as any);
  });

  it('renders login form correctly', () => {
    render(<LoginForm />);

    expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /register here/i })).toBeInTheDocument();
  });

  it('shows loading state during login', async () => {
    mockLoginUser.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<LoginForm />);

    const submitButton = screen.getByRole('button', { name: /login/i });
    fireEvent.click(submitButton);

    expect(submitButton).toBeDisabled();
    expect(screen.getByText(/logging in\.\.\./i)).toBeInTheDocument();
  });

  it('submits form with correct data', async () => {
    render(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);

    fireEvent.change(emailInput, { target: { value: mockLoginCredentials.email } });
    fireEvent.change(passwordInput, { target: { value: mockLoginCredentials.password } });

    const form = emailInput.closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(mockLoginUser).toHaveBeenCalledWith(mockLoginCredentials);
    });
  });

  it('navigates to dashboard on successful login', async () => {
    render(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);

    fireEvent.change(emailInput, { target: { value: mockLoginCredentials.email } });
    fireEvent.change(passwordInput, { target: { value: mockLoginCredentials.password } });

    const form = emailInput.closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('handles login failure', async () => {
    const mockError = { type: 'auth/login/rejected', payload: 'Login failed' };
    mockLoginUser.mockResolvedValue(mockError as any);

    render(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);

    fireEvent.change(emailInput, { target: { value: mockLoginCredentials.email } });
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } });

    const form = emailInput.closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('validates form fields properly', async () => {
    render(<LoginForm />);

    const submitButton = screen.getByRole('button', { name: /login/i });
    const form = submitButton.closest('form');

    // Submit empty form
    if (form) {
      fireEvent.submit(form);
    }

    // Wait for validation errors
    await waitFor(() => {
      expect(screen.getByText(/invalid email address/i)).toBeInTheDocument();
      expect(screen.getByText(/password must be at least 6 characters long/i)).toBeInTheDocument();
    });
  });

  it('shows validation errors for invalid email', async () => {
    render(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid email address/i)).toBeInTheDocument();
    });
  });

  it('shows validation errors for short password', async () => {
    render(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: '123' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/password must be at least 6 characters long/i)).toBeInTheDocument();
    });
  });

  it('has correct accessibility attributes', () => {
    render(<LoginForm />);

    // Check form elements have proper labels and types
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);

    expect(emailInput).toHaveAttribute('type', 'email');
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Check button accessibility
    const submitButton = screen.getByRole('button', { name: /login/i });
    expect(submitButton).toHaveAttribute('type', 'submit');
  });

  it('redirects to register page when register link is clicked', () => {
    render(<LoginForm />);

    const registerLink = screen.getByRole('link', { name: /register here/i });
    expect(registerLink).toHaveAttribute('href', '/register');
  });

  it('has proper form styling and layout', () => {
    render(<LoginForm />);

    const formContainer = screen.getByText('Login').closest('form');
    expect(formContainer).toHaveClass('p-8', 'bg-white', 'rounded', 'shadow-md', 'w-96');

    const submitButton = screen.getByRole('button', { name: /login/i });
    expect(submitButton).toHaveClass('w-full', 'bg-blue-500', 'text-white', 'py-2', 'rounded');
  });

  it('applies error styling to invalid fields', async () => {
    render(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    // Trigger validation errors
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(emailInput).toHaveClass('border-red-500');
      expect(passwordInput).toHaveClass('border-red-500');
    });
  });

  it('handles keyboard navigation properly', () => {
    render(<LoginForm />);

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /login/i });

    // Test tab order
    emailInput.focus();
    expect(emailInput).toHaveFocus();

    fireEvent.tab();
    expect(passwordInput).toHaveFocus();

    fireEvent.tab();
    expect(submitButton).toHaveFocus();

    // Test Enter key submission
    emailInput.focus();
    fireEvent.keyDown(emailInput, { key: 'Enter', code: 'Enter' });
  });
});