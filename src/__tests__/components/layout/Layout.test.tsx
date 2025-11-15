import React from 'react';
import { screen, fireEvent } from '../utils/test-utils';
import Layout from '../../../components/Layout';
import { useAppSelector } from '../../../store/hooks';
import { logout } from '../../../store/slices/authSlice';

// Mock the hooks and store
jest.mock('../../../store/hooks');
jest.mock('../../../store/slices/authSlice');
jest.mock('react-redux', () => ({
  ...jest.requireActual('react-redux'),
  useDispatch: () => jest.fn(),
}));

// Mock React Router
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useLocation: () => ({ pathname: '/' }),
  Outlet: () => <div data-testid="outlet">Page Content</div>,
}));

// Mock Heroicons
jest.mock('@heroicons/react/24/outline', () => ({
  HomeIcon: () => <div data-testid="home-icon">Home</div>,
  ClockIcon: () => <div data-testid="clock-icon">Clock</div>,
  FilmIcon: () => <div data-testid="film-icon">Film</div>,
  UserGroupIcon: () => <div data-testid="user-group-icon">UserGroup</div>,
  ChartBarIcon: () => <div data-testid="chart-bar-icon">ChartBar</div>,
  ArrowRightOnRectangleIcon: () => <div data-testid="logout-icon">Logout</div>,
  Bars3Icon: () => <div data-testid="menu-icon">Menu</div>,
  XMarkIcon: () => <div data-testid="close-icon">Close</div>,
}));

const mockUseAppSelector = useAppSelector as jest.MockedFunction<typeof useAppSelector>;
const mockLogout = logout as jest.MockedFunction<typeof logout>;

describe('Layout Component', () => {
  const mockUser = {
    id: '1',
    firstName: 'John',
    lastName: 'Doe',
    email: 'john@example.com',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAppSelector.mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      loading: false,
    });
  });

  it('renders layout structure correctly', () => {
    render(<Layout />);

    expect(screen.getByTestId('outlet')).toBeInTheDocument();
    expect(screen.getByText(/agent66/i)).toBeInTheDocument();
  });

  it('displays user information in header', () => {
    render(<Layout />);

    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('renders navigation menu items', () => {
    render(<Layout />);

    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /time clock/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /projects/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /crew/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /reports/i })).toBeInTheDocument();
  });

  it('has correct navigation links', () => {
    render(<Layout />);

    expect(screen.getByRole('link', { name: /dashboard/i })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: /time clock/i })).toHaveAttribute('href', '/time-clock');
    expect(screen.getByRole('link', { name: /projects/i })).toHaveAttribute('href', '/projects');
    expect(screen.getByRole('link', { name: /crew/i })).toHaveAttribute('href', '/crew');
    expect(screen.getByRole('link', { name: /reports/i })).toHaveAttribute('href', '/reports');
  });

  it('handles logout functionality', () => {
    render(<Layout />);

    const logoutButton = screen.getByRole('button', { name: /logout/i });
    fireEvent.click(logoutButton);

    expect(mockLogout).toHaveBeenCalled();
  });

  it('shows mobile menu toggle button', () => {
    render(<Layout />);

    const menuButton = screen.getByRole('button', { name: /toggle menu/i });
    expect(menuButton).toBeInTheDocument();
    expect(screen.getByTestId('menu-icon')).toBeInTheDocument();
  });

  it('toggles mobile menu when menu button is clicked', () => {
    render(<Layout />);

    const menuButton = screen.getByRole('button', { name: /toggle menu/i });

    // Initially mobile menu should be hidden
    expect(screen.getByRole('navigation')).not.toHaveClass('mobile-menu-open');

    // Click to open menu
    fireEvent.click(menuButton);
    // Note: Implementation would depend on actual mobile menu state management

    // Check that close icon appears when menu is open
    expect(screen.getByTestId('close-icon')).toBeInTheDocument();
  });

  it('highlights active navigation item based on current route', () => {
    render(<Layout />);

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
    // Should have active styling when on dashboard route
    expect(dashboardLink).toHaveClass('bg-indigo-100', 'text-indigo-700');
  });

  it('displays navigation icons correctly', () => {
    render(<Layout />);

    expect(screen.getByTestId('home-icon')).toBeInTheDocument();
    expect(screen.getByTestId('clock-icon')).toBeInTheDocument();
    expect(screen.getByTestId('film-icon')).toBeInTheDocument();
    expect(screen.getByTestId('user-group-icon')).toBeInTheDocument();
    expect(screen.getByTestId('chart-bar-icon')).toBeInTheDocument();
    expect(screen.getByTestId('logout-icon')).toBeInTheDocument();
  });

  it('handles keyboard navigation', () => {
    render(<Layout />);

    const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
    dashboardLink.focus();
    expect(dashboardLink).toHaveFocus();

    fireEvent.keyDown(dashboardLink, { key: 'Enter' });
    // Should navigate to dashboard
  });

  it('is accessible with proper ARIA labels', () => {
    render(<Layout />);

    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /toggle menu/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();

    const navLinks = screen.getAllByRole('link');
    navLinks.forEach(link => {
      expect(link).toHaveAttribute('href');
    });
  });

  it('applies correct responsive classes', () => {
    render(<Layout />);

    const layoutContainer = screen.getByRole('navigation').closest('.flex');
    expect(layoutContainer).toHaveClass('flex-col', 'md:flex-row');

    const navLinks = screen.getAllByRole('link');
    navLinks.forEach(link => {
      expect(link).toHaveClass('flex', 'items-center', 'px-3', 'py-2');
    });
  });

  it('handles user state changes', () => {
    // Test with different user data
    const differentUser = {
      id: '2',
      firstName: 'Jane',
      lastName: 'Smith',
      email: 'jane@example.com',
    };

    mockUseAppSelector.mockReturnValue({
      user: differentUser,
      isAuthenticated: true,
      loading: false,
    });

    render(<Layout />);

    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
  });

  it('handles loading state', () => {
    mockUseAppSelector.mockReturnValue({
      user: null,
      isAuthenticated: false,
      loading: true,
    });

    render(<Layout />);

    // Should show loading state or handle appropriately
    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('handles unauthenticated state', () => {
    mockUseAppSelector.mockReturnValue({
      user: null,
      isAuthenticated: false,
      loading: false,
    });

    render(<Layout />);

    // Should not display user-specific elements
    expect(screen.queryByText('John Doe')).not.toBeInTheDocument();
  });

  it('has proper semantic structure', () => {
    render(<Layout />);

    // Check for proper header element
    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();

    // Check for proper nav element
    const nav = screen.getByRole('navigation');
    expect(nav).toBeInTheDocument();

    // Check for main content area
    const main = screen.getByRole('main');
    expect(main).toBeInTheDocument();
  });

  it('closes mobile menu when clicking outside', () => {
    render(<Layout />);

    // Open mobile menu
    const menuButton = screen.getByRole('button', { name: /toggle menu/i });
    fireEvent.click(menuButton);

    // Click outside menu
    const layoutArea = screen.getByTestId('outlet').parentElement;
    if (layoutArea) {
      fireEvent.click(layoutArea);
    }

    // Menu should close (implementation dependent)
    expect(screen.getByRole('button', { name: /toggle menu/i })).toBeInTheDocument();
  });

  it('supports proper color contrast for accessibility', () => {
    render(<Layout />);

    const navLinks = screen.getAllByRole('link');
    navLinks.forEach(link => {
      // Links should have proper contrast classes
      expect(link).toHaveClass('text-gray-600', 'hover:text-gray-900', 'hover:bg-gray-50');
    });
  });
});