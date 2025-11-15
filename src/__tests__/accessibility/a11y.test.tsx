import { render, screen } from '../utils/test-utils';
import LoginForm from '../../components/LoginForm';
import RegisterForm from '../../components/RegisterForm';
import Dashboard from '../../components/Dashboard';
import { axe, toHaveNoViolations } from 'jest-axe';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock necessary dependencies
jest.mock('../../store/hooks', () => ({
  useAppSelector: () => ({ user: { id: '1', firstName: 'Test', lastName: 'User' } }),
}));

jest.mock('@tanstack/react-query', () => ({
  useQuery: () => ({ data: { crew: { total: 0, active: 0 }, projects: { active: 0 }, recentActivity: [] }, isLoading: false }),
}));

jest.mock('@heroicons/react/24/outline', () => ({
  ClockIcon: () => <div>Icon</div>,
  FilmIcon: () => <div>Icon</div>,
  UserGroupIcon: () => <div>Icon</div>,
  ChartBarIcon: () => <div>Icon</div>,
  CurrencyDollarIcon: () => <div>Icon</div>,
  PlayIcon: () => <div>Icon</div>,
  StopIcon: () => <div>Icon</div>,
  CalendarIcon: () => <div>Icon</div>,
  MapPinIcon: () => <div>Icon</div>,
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  Link: ({ children, to, ...props }: any) => <a href={to} {...props}>{children}</a>,
}));

describe('Accessibility Tests', () => {
  describe('LoginForm Accessibility', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(<LoginForm />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper form labels and descriptions', () => {
      render(<LoginForm />);

      // Check that all form fields have proper labels
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();

      // Check that labels are properly associated with inputs
      const emailInput = screen.getByLabelText(/email/i);
      expect(emailInput).toHaveAttribute('type', 'email');

      const passwordInput = screen.getByLabelText(/password/i);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });

    it('should have proper button accessibility', () => {
      render(<LoginForm />);

      const submitButton = screen.getByRole('button', { name: /login/i });
      expect(submitButton).toHaveAttribute('type', 'submit');
      expect(submitButton).toBeEnabled();
    });

    it('should support keyboard navigation', () => {
      render(<LoginForm />);

      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /login/i });

      // Test tab order
      emailInput.focus();
      expect(emailInput).toHaveFocus();

      passwordInput.focus();
      expect(passwordInput).toHaveFocus();

      submitButton.focus();
      expect(submitButton).toHaveFocus();
    });

    it('should announce form validation errors', async () => {
      render(<LoginForm />);

      const submitButton = screen.getByRole('button', { name: /login/i });
      fireEvent.click(submitButton);

      // Check that error messages are associated with inputs
      await waitFor(() => {
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument();
        expect(screen.getByText(/password must be at least 6 characters long/i)).toBeInTheDocument();
      });
    });
  });

  describe('RegisterForm Accessibility', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(<RegisterForm />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper form structure', () => {
      render(<RegisterForm />);

      expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();

      const nameInput = screen.getByLabelText(/name/i);
      expect(nameInput).toHaveAttribute('type', 'text');

      const emailInput = screen.getByLabelText(/email/i);
      expect(emailInput).toHaveAttribute('type', 'email');

      const passwordInput = screen.getByLabelText(/^password/i);
      expect(passwordInput).toHaveAttribute('type', 'password');

      const confirmPasswordInput = screen.getByLabelText(/confirm password/i);
      expect(confirmPasswordInput).toHaveAttribute('type', 'password');
    });

    it('should support keyboard navigation and form submission', () => {
      render(<RegisterForm />);

      const inputs = screen.getAllByRole('textbox').concat(screen.getAllByRole('combobox'));
      inputs.forEach(input => {
        input.focus();
        expect(input).toHaveFocus();
      });
    });
  });

  describe('Dashboard Accessibility', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(<Dashboard />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper heading hierarchy', () => {
      render(<Dashboard />);

      // Check for proper heading structure (h1, h2, h3)
      const mainHeading = screen.getByRole('heading', { level: 1 });
      expect(mainHeading).toBeInTheDocument();
      expect(mainHeading).toHaveTextContent(/dashboard/i);

      // Should have subheadings for sections
      const subheadings = screen.getAllByRole('heading', { level: 2 });
      expect(subheadings.length).toBeGreaterThan(0);
    });

    it('should have proper link accessibility', () => {
      render(<Dashboard />);

      const links = screen.getAllByRole('link');
      links.forEach(link => {
        expect(link).toHaveAttribute('href');

        // Links should have accessible names
        expect(link).toHaveAttribute('aria-label') || expect(link.textContent).toBeTruthy();
      });

      // Check specific navigation links
      expect(screen.getByRole('link', { name: /clock/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /projects/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /crew/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /reports/i })).toBeInTheDocument();
    });

    it('should have proper semantic structure', () => {
      render(<Dashboard />);

      // Should have main landmark
      expect(screen.getByRole('main')).toBeInTheDocument();

      // Should have navigation landmarks
      expect(screen.getAllByRole('navigation')).not.toHaveLength(0);

      // Should have proper sections
      const sections = screen.getAllByRole('region');
      expect(sections.length).toBeGreaterThan(0);
    });

    it('should have proper color contrast requirements', () => {
      render(<Dashboard />);

      // Check that interactive elements have proper contrast
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        // Buttons should have proper contrast classes
        expect(button).toHaveClass(/text-white/); // Light text on dark backgrounds
      });

      const links = screen.getAllByRole('link');
      links.forEach(link => {
        // Links should have hover states
        expect(link).toHaveClass(/hover:/);
      });
    });

    it('should support keyboard navigation', () => {
      render(<Dashboard />);

      const links = screen.getAllByRole('link');
      links.forEach(link => {
        link.focus();
        expect(link).toHaveFocus();
      });

      // Test tab order
      const firstLink = links[0];
      firstLink.focus();
      expect(firstLink).toHaveFocus();

      // Should be able to tab through all interactive elements
      for (let i = 1; i < links.length; i++) {
        fireEvent.tab();
        expect(links[i]).toHaveFocus();
      }
    });

    it('should provide sufficient information for screen readers', () => {
      render(<Dashboard />);

      // Check that important information has proper labels
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();

      // Stats should have proper labels
      expect(screen.getByText(/total crew/i)).toBeInTheDocument();
      expect(screen.getByText(/active projects/i)).toBeInTheDocument();
      expect(screen.getByText(/today's hours/i)).toBeInTheDocument();

      // Quick actions should be properly labeled
      expect(screen.getByRole('link', { name: /clock/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /projects/i })).toBeInTheDocument();
    });
  });

  describe('Form Validation Accessibility', () => {
    it('should announce validation errors to screen readers', async () => {
      render(<LoginForm />);

      const submitButton = screen.getByRole('button', { name: /login/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        // Error messages should be associated with inputs
        const emailInput = screen.getByLabelText(/email/i);
        expect(emailInput).toHaveAttribute('aria-invalid', 'true');

        const passwordInput = screen.getByLabelText(/password/i);
        expect(passwordInput).toHaveAttribute('aria-invalid', 'true');
      });
    });

    it('should provide clear error messages', async () => {
      render(<RegisterForm />);

      const submitButton = screen.getByRole('button', { name: /register/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        // Error messages should be specific and helpful
        expect(screen.getByText(/name must be at least 2 characters long/i)).toBeInTheDocument();
        expect(screen.getByText(/invalid email address/i)).toBeInTheDocument();
        expect(screen.getByText(/password must be at least 6 characters long/i)).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design Accessibility', () => {
    it('should maintain accessibility on different screen sizes', () => {
      // Test mobile view
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      });

      const { container: mobileContainer } = render(<Dashboard />);

      // Should still be accessible on mobile
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
      expect(screen.getAllByRole('link')).not.toHaveLength(0);

      // Test desktop view
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024,
      });

      const { container: desktopContainer } = render(<Dashboard />);

      // Should still be accessible on desktop
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
      expect(screen.getAllByRole('link')).not.toHaveLength(0);
    });
  });

  describe('Focus Management', () => {
    it('should manage focus properly during form interactions', () => {
      render(<LoginForm />);

      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /login/i });

      // Focus should move through form logically
      emailInput.focus();
      expect(emailInput).toHaveFocus();

      passwordInput.focus();
      expect(passwordInput).toHaveFocus();

      submitButton.focus();
      expect(submitButton).toHaveFocus();
    });

    it('should maintain focus after form submission', async () => {
      render(<RegisterForm />);

      const submitButton = screen.getByRole('button', { name: /register/i });

      // Focus the submit button
      submitButton.focus();
      expect(submitButton).toHaveFocus();

      // Submit form (even with errors, focus should remain manageable)
      fireEvent.click(submitButton);

      // Focus should still be on an appropriate element
      expect(document.activeElement).toBeInTheDocument();
    });
  });

  describe('ARIA Labels and Descriptions', () => {
    it('should provide appropriate ARIA labels', () => {
      render(<Dashboard />);

      // Check that navigation has proper labels
      const nav = screen.getByRole('navigation');
      expect(nav).toBeInTheDocument();

      // Links should have descriptive text
      const clockLink = screen.getByRole('link', { name: /clock/i });
      expect(clockLink).toBeInTheDocument();

      // Should have aria-label or descriptive content
      expect(clockLink.textContent || clockLink.getAttribute('aria-label')).toBeTruthy();
    });

    it('should use semantic HTML properly', () => {
      render(<LoginForm />);

      // Should use proper form elements
      expect(screen.getByRole('form')).toBeInTheDocument();

      // Should use proper input types
      expect(screen.getByLabelText(/email/i)).toHaveAttribute('type', 'email');
      expect(screen.getByLabelText(/password/i)).toHaveAttribute('type', 'password');

      // Should use proper button types
      expect(screen.getByRole('button', { name: /login/i })).toHaveAttribute('type', 'submit');
    });
  });
});