import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAppSelector } from '../store/hooks';
import {
  ClockIcon,
  FilmIcon,
  UserGroupIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  PlayIcon,
  StopIcon,
  CalendarIcon,
  MapPinIcon,
} from '@heroicons/react/24/outline';
import { format, isToday, startOfWeek, endOfWeek } from 'date-fns';

interface DashboardStats {
  crew: {
    total: number;
    active: number;
  };
  projects: {
    active: number;
  };
  recentActivity: Array<{
    id: string;
    user: {
      id: string;
      firstName: string;
      lastName: string;
    };
    project: {
      id: string;
      title: string;
    };
    date: string;
  }>;
}

interface TimeEntry {
  id: string;
  clockIn: string;
  clockOut?: string;
  totalHours?: number;
  status: string;
  project: {
    id: string;
    title: string;
    location?: string;
  };
}

const Dashboard: React.FC = () => {
  const { user } = useAppSelector((state) => state.auth);

  // Fetch dashboard stats
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: async () => {
      const response = await fetch('/api/crew/stats/dashboard');
      if (!response.ok) throw new Error('Failed to fetch dashboard stats');
      return response.json();
    },
  });

  // Fetch active time entry
  const { data: activeEntryData } = useQuery({
    queryKey: ['activeTimeEntry', user?.id],
    queryFn: async () => {
      if (!user?.id) return null;
      const response = await fetch(`/api/time-entries/active/${user.id}`);
      if (!response.ok) throw new Error('Failed to fetch active time entry');
      return response.json();
    },
    enabled: !!user?.id,
  });

  // Fetch today's time entries
  const { data: todayEntriesData } = useQuery({
    queryKey: ['todayTimeEntries', user?.id],
    queryFn: async () => {
      if (!user?.id) return [];
      const today = new Date().toISOString().split('T')[0];
      const response = await fetch(`/api/time-entries?userId=${user.id}&startDate=${today}&endDate=${today}`);
      if (!response.ok) throw new Error('Failed to fetch today\'s entries');
      const data = await response.json();
      return data.timeEntries;
    },
    enabled: !!user?.id,
  });

  // Fetch recent projects
  const { data: projectsData } = useQuery({
    queryKey: ['recentProjects'],
    queryFn: async () => {
      const response = await fetch('/api/projects?limit=6&sortBy=createdAt&sortOrder=desc');
      if (!response.ok) throw new Error('Failed to fetch recent projects');
      return response.json();
    },
  });

  const stats = statsData as DashboardStats;
  const activeEntry = activeEntryData?.activeEntry;
  const todayEntries = todayEntriesData || [];
  const recentProjects = projectsData?.projects || [];

  const todayTotalHours = todayEntries.reduce((total: number, entry: TimeEntry) => {
    return total + (entry.totalHours || 0);
  }, 0);

  const getProjectStatusColor = (status: string) => {
    const colors: { [key: string]: string } = {
      PLANNING: 'bg-gray-100 text-gray-800',
      'PRE_PRODUCTION': 'bg-blue-100 text-blue-800',
      PRODUCTION: 'bg-green-100 text-green-800',
      'POST_PRODUCTION': 'bg-purple-100 text-purple-800',
      COMPLETED: 'bg-emerald-100 text-emerald-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getProjectStatusLabel = (status: string) => {
    return status.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Welcome back! Here's what's happening on your productions.</p>
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-4 gap-4 mb-8">
        <Link
          to="/time-clock"
          className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow border-2 border-transparent hover:border-indigo-500"
        >
          <div className="flex items-center">
            <div className="p-3 bg-indigo-100 rounded-full">
              {activeEntry ? (
                <StopIcon className="h-6 w-6 text-indigo-600" />
              ) : (
                <PlayIcon className="h-6 w-6 text-indigo-600" />
              )}
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {activeEntry ? 'Clock Out' : 'Clock In'}
              </h3>
              <p className="text-sm text-gray-500">
                {activeEntry ? 'End your shift' : 'Start your shift'}
              </p>
            </div>
          </div>
        </Link>

        <Link
          to="/projects"
          className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow border-2 border-transparent hover:border-indigo-500"
        >
          <div className="flex items-center">
            <div className="p-3 bg-green-100 rounded-full">
              <FilmIcon className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">Projects</h3>
              <p className="text-sm text-gray-500">Manage productions</p>
            </div>
          </div>
        </Link>

        <Link
          to="/crew"
          className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow border-2 border-transparent hover:border-indigo-500"
        >
          <div className="flex items-center">
            <div className="p-3 bg-purple-100 rounded-full">
              <UserGroupIcon className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">Crew</h3>
              <p className="text-sm text-gray-500">Team management</p>
            </div>
          </div>
        </Link>

        <Link
          to="/reports"
          className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow border-2 border-transparent hover:border-indigo-500"
        >
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 rounded-full">
              <ChartBarIcon className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">Reports</h3>
              <p className="text-sm text-gray-500">Analytics & insights</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Stats Overview */}
      <div className="grid md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-3 bg-blue-100 rounded-full">
              <UserGroupIcon className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Total Crew</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.crew.total || 0}</p>
              <p className="text-xs text-green-600">+{stats?.crew.active || 0} active</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 rounded-full">
              <FilmIcon className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Active Projects</p>
              <p className="text-2xl font-bold text-gray-900">{stats?.projects.active || 0}</p>
              <p className="text-xs text-gray-500">In production</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-3 bg-indigo-100 rounded-full">
              <ClockIcon className="h-6 w-6 text-indigo-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">Today's Hours</p>
              <p className="text-2xl font-bold text-gray-900">{todayTotalHours.toFixed(1)}</p>
              <p className="text-xs text-gray-500">{todayEntries.length} entries</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 rounded-full">
              <CurrencyDollarIcon className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-500">This Week</p>
              <p className="text-2xl font-bold text-gray-900">
                {todayEntries
                  .filter(entry => isToday(new Date(entry.date)))
                  .reduce((total, entry) => total + (entry.totalHours || 0), 0)
                  .toFixed(1)}
              </p>
              <p className="text-xs text-gray-500">Hours worked</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Active Time Entry */}
        {activeEntry && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Currently Clocked In</h3>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <div className="p-2 bg-green-100 rounded-full">
                  <ClockIcon className="h-5 w-5 text-green-600" />
                </div>
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-green-800">Active Time Entry</h4>
                  <div className="mt-1 text-sm text-green-700">
                    <p>Project: {activeEntry.project.title}</p>
                    <p>Started: {format(new Date(activeEntry.clockIn), 'h:mm a')}</p>
                    {activeEntry.location && (
                      <p className="flex items-center mt-1">
                        <MapPinIcon className="h-4 w-4 mr-1" />
                        {activeEntry.location}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Recent Projects */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Recent Projects</h3>
            <Link
              to="/projects"
              className="text-sm text-indigo-600 hover:text-indigo-800"
            >
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {recentProjects.slice(0, 4).map((project: any) => (
              <div
                key={project.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer"
                onClick={() => window.location.href = `/projects/${project.id}`}
              >
                <div>
                  <h4 className="text-sm font-medium text-gray-900">{project.title}</h4>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className={`text-xs px-2 py-1 rounded-full ${getProjectStatusColor(project.status)}`}>
                      {getProjectStatusLabel(project.status)}
                    </span>
                    <span className="text-xs text-gray-500">
                      {project.type.replace('_', ' ')}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-900">
                    {project._count.members} crew
                  </div>
                  <div className="text-xs text-gray-500">
                    {project._count.timeEntries} entries
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {stats?.recentActivity?.slice(0, 5).map((activity) => (
              <div key={activity.id} className="flex items-center space-x-3 p-2">
                <div className="p-2 bg-gray-100 rounded-full">
                  <ClockIcon className="h-4 w-4 text-gray-600" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-900">
                    <span className="font-medium">
                      {activity.user.firstName} {activity.user.lastName}
                    </span>{' '}
                    logged time for
                    <span className="font-medium ml-1">{activity.project.title}</span>
                  </p>
                  <p className="text-xs text-gray-500">
                    {format(new Date(activity.date), 'MMM d, yyyy h:mm a')}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;