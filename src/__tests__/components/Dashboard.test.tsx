import React from 'react';
import { screen, fireEvent, waitFor } from '../utils/test-utils';
import Dashboard from '../../components/Dashboard';
import { useAppSelector } from '../../store/hooks';
import { mockFetchResponse, resetMocks, createQueryResponse } from '../utils/react-query-test-utils';

// Mock hooks and utilities
jest.mock('../../store/hooks');
jest.mock('@tanstack/react-query', () => ({
  ...jest.requireActual('@tanstack/react-query'),
  useQuery: jest.fn(),
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  format: jest.fn((date, formatStr) => '2024-01-15 10:30 AM'),
  isToday: jest.fn(() => true),
  startOfWeek: jest.fn(() => new Date('2024-01-14')),
  endOfWeek: jest.fn(() => new Date('2024-01-20')),
}));

// Mock Heroicons
jest.mock('@heroicons/react/24/outline', () => ({
  ClockIcon: () => <div data-testid="clock-icon">Clock</div>,
  FilmIcon: () => <div data-testid="film-icon">Film</div>,
  UserGroupIcon: () => <div data-testid="user-group-icon">UserGroup</div>,
  ChartBarIcon: () => <div data-testid="chart-bar-icon">ChartBar</div>,
  CurrencyDollarIcon: () => <div data-testid="currency-dollar-icon">Currency</div>,
  PlayIcon: () => <div data-testid="play-icon">Play</div>,
  StopIcon: () => <div data-testid="stop-icon">Stop</div>,
  CalendarIcon: () => <div data-testid="calendar-icon">Calendar</div>,
  MapPinIcon: () => <div data-testid="map-pin-icon">MapPin</div>,
}));

// Mock Link component
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
}));

const mockUseAppSelector = useAppSelector as jest.MockedFunction<typeof useAppSelector>;
const mockUseQuery = require('@tanstack/react-query').useQuery;

describe('Dashboard', () => {
  const mockUser = { id: '1', firstName: 'John', lastName: 'Doe' };

  const mockStatsData = {
    crew: { total: 25, active: 18 },
    projects: { active: 5 },
    recentActivity: [
      {
        id: '1',
        user: { id: '1', firstName: 'John', lastName: 'Doe' },
        project: { id: '1', title: 'Film Project Alpha' },
        date: '2024-01-15T10:30:00Z',
      },
    ],
  };

  const mockProjectsData = {
    projects: [
      {
        id: '1',
        title: 'Film Project Alpha',
        status: 'PRODUCTION',
        type: 'FEATURE_FILM',
        _count: { members: 12, timeEntries: 45 },
      },
      {
        id: '2',
        title: 'Commercial Beta',
        status: 'POST_PRODUCTION',
        type: 'COMMERCIAL',
        _count: { members: 8, timeEntries: 23 },
      },
    ],
  };

  const mockActiveEntryData = {
    activeEntry: {
      id: '1',
      clockIn: '2024-01-15T08:00:00Z',
      status: 'ACTIVE',
      project: {
        id: '1',
        title: 'Film Project Alpha',
        location: 'Studio A',
      },
      location: 'Studio A',
    },
  };

  const mockTodayEntriesData = [
    {
      id: '1',
      clockIn: '2024-01-15T08:00:00Z',
      clockOut: '2024-01-15T16:00:00Z',
      totalHours: 8,
      status: 'COMPLETED',
      date: '2024-01-15T08:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    resetMocks();
    mockUseAppSelector.mockReturnValue({ user: mockUser });

    // Mock all useQuery calls
    mockUseQuery
      .mockReturnValueOnce({ data: mockStatsData, isLoading: false }) // dashboardStats
      .mockReturnValueOnce({ data: mockActiveEntryData, isLoading: false }) // activeTimeEntry
      .mockReturnValueOnce({ data: mockTodayEntriesData, isLoading: false }) // todayTimeEntries
      .mockReturnValueOnce({ data: mockProjectsData, isLoading: false }); // recentProjects
  });

  it('renders dashboard header correctly', () => {
    render(<Dashboard />);

    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByText(/welcome back! here's what's happening on your productions\./i)).toBeInTheDocument();
  });

  it('displays loading state when stats are loading', () => {
    mockUseQuery.mockReturnValueOnce({ isLoading: true }); // dashboardStats loading

    render(<Dashboard />);

    expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
    expect(screen.getByTestId('clock-icon')).toBeInTheDocument();
  });

  it('renders quick action cards', () => {
    render(<Dashboard />);

    // Check quick action links exist
    expect(screen.getByRole('link', { name: /clock in/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /projects/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /crew/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /reports/i })).toBeInTheDocument();

    // Check proper href attributes
    expect(screen.getByRole('link', { name: /clock in/i })).toHaveAttribute('href', '/time-clock');
    expect(screen.getByRole('link', { name: /projects/i })).toHaveAttribute('href', '/projects');
  });

  it('shows clock out button when active entry exists', () => {
    render(<Dashboard />);

    expect(screen.getByRole('link', { name: /clock out/i })).toBeInTheDocument();
    expect(screen.getByTestId('stop-icon')).toBeInTheDocument();
    expect(screen.getByText(/end your shift/i)).toBeInTheDocument();
  });

  it('shows clock in button when no active entry exists', () => {
    mockUseQuery.mockReturnValueOnce({ data: null, isLoading: false }); // No active entry

    render(<Dashboard />);

    expect(screen.getByRole('link', { name: /clock in/i })).toBeInTheDocument();
    expect(screen.getByTestId('play-icon')).toBeInTheDocument();
    expect(screen.getByText(/start your shift/i })).toBeInTheDocument();
  });

  it('displays stats overview correctly', () => {
    render(<Dashboard />);

    expect(screen.getByText(/total crew/i)).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText(/\+18 active/i)).toBeInTheDocument();

    expect(screen.getByText(/active projects/i)).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();

    expect(screen.getByText(/today's hours/i)).toBeInTheDocument();
    expect(screen.getByText('8.0')).toBeInTheDocument();

    expect(screen.getByText(/this week/i)).toBeInTheDocument();
  });

  it('displays active time entry when present', () => {
    render(<Dashboard />);

    expect(screen.getByText(/currently clocked in/i)).toBeInTheDocument();
    expect(screen.getByText(/active time entry/i)).toBeInTheDocument();
    expect(screen.getByText(/project: film project alpha/i)).toBeInTheDocument();
    expect(screen.getByText(/started: 2024-01-15 10:30 am/i)).toBeInTheDocument();
    expect(screen.getByText(/studio a/i)).toBeInTheDocument();
    expect(screen.getByTestId('map-pin-icon')).toBeInTheDocument();
  });

  it('does not display active time entry when none exists', () => {
    mockUseQuery.mockReturnValueOnce({ data: null, isLoading: false }); // No active entry

    render(<Dashboard />);

    expect(screen.queryByText(/currently clocked in/i)).not.toBeInTheDocument();
  });

  it('displays recent projects correctly', () => {
    render(<Dashboard />);

    expect(screen.getByText(/recent projects/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /view all/i })).toHaveAttribute('href', '/projects');

    expect(screen.getByText('Film Project Alpha')).toBeInTheDocument();
    expect(screen.getByText('Production')).toBeInTheDocument();
    expect(screen.getByText('FEATURE_FILM')).toBeInTheDocument();
    expect(screen.getByText('12 crew')).toBeInTheDocument();
    expect(screen.getByText('45 entries')).toBeInTheDocument();

    expect(screen.getByText('Commercial Beta')).toBeInTheDocument();
    expect(screen.getByText('Post Production')).toBeInTheDocument();
    expect(screen.getByText('COMMERCIAL')).toBeInTheDocument();
  });

  it('displays recent activity correctly', () => {
    render(<Dashboard />);

    expect(screen.getByText(/recent activity/i)).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText(/logged time for/i)).toBeInTheDocument();
    expect(screen.getByText('Film Project Alpha')).toBeInTheDocument();
    expect(screen.getByText(/2024-01-15 10:30 am/i)).toBeInTheDocument();
  });

  it('calculates today\'s total hours correctly', () => {
    const entriesWithDifferentHours = [
      { totalHours: 4 },
      { totalHours: 3.5 },
      { totalHours: 2.5 },
    ];

    mockUseQuery.mockReturnValueOnce({ data: entriesWithDifferentHours, isLoading: false });

    render(<Dashboard />);

    // Should show 10.0 total hours (4 + 3.5 + 2.5)
    const todayHoursElement = screen.getByText('10.0');
    expect(todayHoursElement).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
    mockUseQuery
      .mockReturnValueOnce({ data: { crew: { total: 0, active: 0 }, projects: { active: 0 }, recentActivity: [] }, isLoading: false })
      .mockReturnValueOnce({ data: null, isLoading: false })
      .mockReturnValueOnce({ data: [], isLoading: false })
      .mockReturnValueOnce({ data: { projects: [] }, isLoading: false });

    render(<Dashboard />);

    expect(screen.getByText('0')).toBeInTheDocument(); // Total crew
    expect(screen.getByText('0')).toBeInTheDocument(); // Active projects
    expect(screen.getByText('0.0')).toBeInTheDocument(); // Today's hours
    expect(screen.queryByText(/recent activity/i)).toBeInTheDocument();
  });

  it('applies correct project status colors and labels', () => {
    render(<Dashboard />);

    const productionBadge = screen.getByText('Production');
    expect(productionBadge).toHaveClass('bg-green-100', 'text-green-800');

    const postProductionBadge = screen.getByText('Post Production');
    expect(postProductionBadge).toHaveClass('bg-purple-100', 'text-purple-800');
  });

  it('navigates to project when project card is clicked', () => {
    // Mock window.location
    delete (window as any).location;
    window.location = { href: '' } as any;

    render(<Dashboard />);

    const projectCard = screen.getByText('Film Project Alpha').closest('.cursor-pointer');
    if (projectCard) {
      fireEvent.click(projectCard);
    }

    expect(window.location.href).toBe('/projects/1');
  });

  it('handles API errors gracefully', () => {
    mockUseQuery
      .mockReturnValueOnce({ error: new Error('Failed to fetch'), isLoading: false, isError: true })
      .mockReturnValueOnce({ data: null, isLoading: false })
      .mockReturnValueOnce({ data: [], isLoading: false })
      .mockReturnValueOnce({ data: { projects: [] }, isLoading: false });

    render(<Dashboard />);

    // Should still render dashboard with default values
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument(); // Default values when API fails
  });

  it('updates when user data changes', () => {
    const newUser = { id: '2', firstName: 'Jane', lastName: 'Smith' };
    mockUseAppSelector.mockReturnValue({ user: newUser });

    render(<Dashboard />);

    // Should call queries with new user ID
    expect(mockUseQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['activeTimeEntry', newUser.id],
        enabled: !!newUser.id,
      })
    );

    expect(mockUseQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['todayTimeEntries', newUser.id],
        enabled: !!newUser.id,
      })
    );
  });

  it('has proper responsive layout classes', () => {
    render(<Dashboard />);

    const quickActionsGrid = screen.getByRole('link', { name: /clock out/i }).closest('.grid');
    expect(quickActionsGrid).toHaveClass('md:grid-cols-4');

    const statsGrid = screen.getByText(/total crew/i).closest('.grid');
    expect(statsGrid).toHaveClass('md:grid-cols-4');

    const contentGrid = screen.getByText(/recent projects/i).closest('.grid');
    expect(contentGrid).toHaveClass('md:grid-cols-2');
  });
});