import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter as Router } from 'react-router-dom';
import { store } from '../store/store';
import LoginForm from './LoginForm';

describe('LoginForm', () => {
  it('renders login form', () => {
    render(
      <Provider store={store}>
        <Router>
          <LoginForm />
        </Router>
      </Provider>
    );

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  it('shows validation errors', async () => {
    render(
      <Provider store={store}>
        <Router>
          <LoginForm />
        </Router>
      </Provider>
    );

    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    expect(await screen.findByText(/invalid email address/i)).toBeInTheDocument();
    expect(await screen.findByText(/password must be at least 6 characters long/i)).toBeInTheDocument();
  });
});