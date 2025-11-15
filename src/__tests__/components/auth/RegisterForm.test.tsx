import React from 'react';
import { screen, fireEvent, waitFor } from '../utils/test-utils';
import RegisterForm from '../../../components/RegisterForm';
import { registerUser } from '../../../store/slices/authSlice';
import { mockRegisterData, mockAxiosSuccess, mockAxiosError } from '../utils/store-test-utils';

// Mock the auth slice actions
jest.mock('../../../store/slices/authSlice');
const mockRegisterUser = registerUser as jest.MockedFunction<typeof registerUser>;

// Mock React Router
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock React Hook Form
jest.mock('react-hook-form', () => ({
  ...jest.requireActual('react-hook-form'),
  useForm: () => ({
    register: jest.fn(),
    handleSubmit: (fn: any) => (e: any) => {
      e.preventDefault();
      fn(mockRegisterData);
    },
    formState: { errors: {} },
  }),
}));

describe('RegisterForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRegisterUser.mockResolvedValue({
      type: 'auth/register/fulfilled',
      payload: { token: 'mock-token' },
    } as any);
  });

  it('renders register form correctly', () => {
    render(<RegisterForm />);

    expect(screen.getByRole('heading', { name: /register/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
    expect(screen.getByText(/already have an account/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /login here/i })).toBeInTheDocument();
  });

  it('shows loading state during registration', async () => {
    mockRegisterUser.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<RegisterForm />);

    const submitButton = screen.getByRole('button', { name: /register/i });
    fireEvent.click(submitButton);

    expect(submitButton).toBeDisabled();
    expect(screen.getByText(/registering\.\.\./i)).toBeInTheDocument();
  });

  it('submits form with correct data', async () => {
    render(<RegisterForm />);

    const form = screen.getByRole('form') || screen.getByText('Register').closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(mockRegisterUser).toHaveBeenCalledWith({
        name: 'Test User',
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('navigates to dashboard on successful registration', async () => {
    render(<RegisterForm />);

    const form = screen.getByRole('form') || screen.getByText('Register').closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('handles registration failure', async () => {
    const mockError = { type: 'auth/register/rejected', payload: 'Registration failed' };
    mockRegisterUser.mockResolvedValue(mockError as any);

    render(<RegisterForm />);

    const form = screen.getByRole('form') || screen.getByText('Register').closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('has correct accessibility attributes', () => {
    render(<RegisterForm />);

    // Check form elements have proper labels
    const nameInput = screen.getByLabelText(/name/i);
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/^password/i);
    const confirmPasswordInput = screen.getByLabelText(/confirm password/i);

    expect(nameInput).toHaveAttribute('type', 'text');
    expect(emailInput).toHaveAttribute('type', 'email');
    expect(passwordInput).toHaveAttribute('type', 'password');
    expect(confirmPasswordInput).toHaveAttribute('type', 'password');

    // Check button accessibility
    const submitButton = screen.getByRole('button', { name: /register/i });
    expect(submitButton).toHaveAttribute('type', 'submit');
  });

  it('redirects to login page when login link is clicked', () => {
    render(<RegisterForm />);

    const loginLink = screen.getByRole('link', { name: /login here/i });
    expect(loginLink).toHaveAttribute('href', '/login');
  });

  it('has proper form styling and layout', () => {
    render(<RegisterForm />);

    const formContainer = screen.getByText('Register').closest('form');
    expect(formContainer).toHaveClass('p-8', 'bg-white', 'rounded', 'shadow-md', 'w-96');

    const submitButton = screen.getByRole('button', { name: /register/i });
    expect(submitButton).toHaveClass('w-full', 'bg-green-500', 'text-white', 'py-2', 'rounded');
  });
});