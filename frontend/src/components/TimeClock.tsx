import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format, differenceInSeconds, isToday } from 'date-fns';
import {
  ClockIcon,
  MapPinIcon,
  CalendarIcon,
  UserCircleIcon,
  PlayIcon,
  StopIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { useAppSelector } from '../store/hooks';

interface TimeEntry {
  id: string;
  clockIn: string;
  clockOut?: string;
  totalHours?: number;
  status: string;
  notes?: string;
  location?: string;
  project: {
    id: string;
    title: string;
    location?: string;
  };
}

interface Project {
  id: string;
  title: string;
  status: string;
  type: string;
}

const TimeClock: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAppSelector((state) => state.auth);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [location, setLocation] = useState('');
  const [breakDuration, setBreakDuration] = useState(0);

  // Get user's active time entry
  const { data: activeEntryData, isLoading: activeLoading } = useQuery({
    queryKey: ['activeTimeEntry', user?.id],
    queryFn: async () => {
      if (!user?.id) return null;
      const response = await fetch(`/api/time-entries/active/${user.id}`);
      if (!response.ok) throw new Error('Failed to fetch active time entry');
      return response.json();
    },
    enabled: !!user?.id,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const activeEntry = activeEntryData?.activeEntry;

  // Get user's projects
  const { data: projectsData, isLoading: projectsLoading } = useQuery({
    queryKey: ['userProjects', user?.id],
    queryFn: async () => {
      if (!user?.id) return [];
      const response = await fetch(`/api/crew/${user?.id}`);
      if (!response.ok) throw new Error('Failed to fetch projects');
      const data = await response.json();
      return data.projectMembers.map((member: any) => member.project);
    },
    enabled: !!user?.id,
  });

  // Get today's time entries
  const { data: todayEntriesData, isLoading: todayLoading } = useQuery({
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
    refetchInterval: 30000,
  });

  // Clock in mutation
  const clockInMutation = useMutation({
    mutationFn: async (clockData: any) => {
      const response = await fetch('/api/time-entries/clock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(clockData),
      });
      if (!response.ok) throw new Error('Failed to clock in');
      return response.json();
    },
    onSuccess: () => {
      toast.success('Clocked in successfully!');
      queryClient.invalidateQueries({ queryKey: ['activeTimeEntry'] });
      queryClient.invalidateQueries({ queryKey: ['todayTimeEntries'] });
      setNotes('');
      setLocation('');
      setBreakDuration(0);
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  // Clock out mutation
  const clockOutMutation = useMutation({
    mutationFn: async (clockData: any) => {
      const response = await fetch('/api/time-entries/clock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(clockData),
      });
      if (!response.ok) throw new Error('Failed to clock out');
      return response.json();
    },
    onSuccess: () => {
      toast.success('Clocked out successfully!');
      queryClient.invalidateQueries({ queryKey: ['activeTimeEntry'] });
      queryClient.invalidateQueries({ queryKey: ['todayTimeEntries'] });
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  // Get current location
  useEffect(() => {
    if (navigator.geolocation && !location) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation(`${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`);
        },
        (error) => {
          console.log('Location access denied:', error);
        }
      );
    }
  }, [location]);

  // Calculate elapsed time
  const [elapsedTime, setElapsedTime] = useState('00:00:00');
  useEffect(() => {
    if (activeEntry?.clockIn) {
      const interval = setInterval(() => {
        const seconds = differenceInSeconds(new Date(), new Date(activeEntry.clockIn));
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        setElapsedTime(`${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`);
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [activeEntry]);

  const handleClockIn = () => {
    if (!selectedProject) {
      toast.error('Please select a project');
      return;
    }

    clockInMutation.mutate({
      userId: user?.id,
      projectId: selectedProject,
      clockIn: new Date().toISOString(),
      notes: notes.trim() || undefined,
      location: location.trim() || undefined,
    });
  };

  const handleClockOut = () => {
    if (!activeEntry) return;

    clockOutMutation.mutate({
      userId: user?.id,
      projectId: activeEntry.project.id,
      clockIn: activeEntry.clockIn,
      clockOut: new Date().toISOString(),
      breakDuration,
      notes: notes.trim() || undefined,
      location: location.trim() || undefined,
    });
  };

  const todayTotalHours = todayEntriesData?.reduce((total: number, entry: TimeEntry) => {
    return total + (entry.totalHours || 0);
  }, 0) || 0;

  if (activeLoading || projectsLoading || todayLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white shadow-lg rounded-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-6 text-white">
          <h1 className="text-2xl font-bold">Time Clock</h1>
          <p className="text-indigo-100">Track your time on set</p>
        </div>

        <div className="p-6">
          {/* Current Status */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <ClockIcon className="h-6 w-6 text-indigo-600" />
                <span className="text-lg font-semibold text-gray-900">
                  {activeEntry ? 'Currently Clocked In' : 'Currently Clocked Out'}
                </span>
              </div>
              {activeEntry && (
                <div className="text-2xl font-mono font-bold text-indigo-600">
                  {elapsedTime}
                </div>
              )}
            </div>

            {activeEntry && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <CheckCircleIcon className="h-6 w-6 text-green-600 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-green-800">Active Time Entry</h3>
                    <div className="mt-1 text-sm text-green-700">
                      <p>Project: {activeEntry.project.title}</p>
                      <p>Clocked in: {format(new Date(activeEntry.clockIn), 'MMM d, yyyy h:mm a')}</p>
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
            )}
          </div>

          {/* Clock In/Out Form */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            {!activeEntry ? (
              /* Clock In Form */
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Project *
                  </label>
                  <select
                    value={selectedProject}
                    onChange={(e) => setSelectedProject(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    required
                  >
                    <option value="">Choose a project...</option>
                    {projectsData?.map((project: Project) => (
                      <option key={project.id} value={project.id}>
                        {project.title} ({project.type})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Notes (optional)
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Any notes about today's work..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    rows={3}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Location
                  </label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Set location or address..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <button
                  onClick={handleClockIn}
                  disabled={!selectedProject || clockInMutation.isPending}
                  className="w-full flex items-center justify-center px-4 py-3 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <PlayIcon className="h-5 w-5 mr-2" />
                  {clockInMutation.isPending ? 'Clocking in...' : 'Clock In'}
                </button>
              </div>
            ) : (
              /* Clock Out Form */
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Current Project
                  </label>
                  <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-md">
                    {activeEntry.project.title}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Break Duration (minutes)
                  </label>
                  <input
                    type="number"
                    value={breakDuration}
                    onChange={(e) => setBreakDuration(Number(e.target.value))}
                    min="0"
                    placeholder="Break duration in minutes"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    End of Day Notes
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Any notes about today's work or wrap-up..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    rows={3}
                  />
                </div>

                <button
                  onClick={handleClockOut}
                  disabled={clockOutMutation.isPending}
                  className="w-full flex items-center justify-center px-4 py-3 bg-red-600 text-white font-medium rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <StopIcon className="h-5 w-5 mr-2" />
                  {clockOutMutation.isPending ? 'Clocking out...' : 'Clock Out'}
                </button>
              </div>
            )}

            {/* Today's Summary */}
            <div className="bg-gray-50 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Today's Summary</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Total Hours:</span>
                  <span className="font-semibold text-lg">{todayTotalHours.toFixed(1)} hrs</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Entries Today:</span>
                  <span className="font-semibold">{todayEntriesData?.length || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Current Status:</span>
                  <span className={`font-semibold ${activeEntry ? 'text-green-600' : 'text-gray-600'}`}>
                    {activeEntry ? 'On Shift' : 'Off Shift'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Time Entries */}
          {todayEntriesData && todayEntriesData.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Today's Time Entries</h3>
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Project
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Clock In
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Clock Out
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Hours
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {todayEntriesData.map((entry: TimeEntry) => (
                        <tr key={entry.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {entry.project.title}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {format(new Date(entry.clockIn), 'h:mm a')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {entry.clockOut ? format(new Date(entry.clockOut), 'h:mm a') : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {entry.totalHours?.toFixed(1) || '-'} hrs
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              entry.status === 'APPROVED'
                                ? 'bg-green-100 text-green-800'
                                : entry.status === 'SUBMITTED'
                                ? 'bg-yellow-100 text-yellow-800'
                                : entry.status === 'REJECTED'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}>
                              {entry.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TimeClock;