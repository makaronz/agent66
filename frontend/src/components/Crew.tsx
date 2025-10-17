import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  MagnifyingGlassIcon,
  UserGroupIcon,
  FunnelIcon,
  EnvelopeIcon,
  PhoneIcon,
  BuildingOfficeIcon,
  ClockIcon,
  CurrencyDollarIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';

interface CrewMember {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  department?: string;
  phone?: string;
  avatar?: string;
  createdAt: string;
  _count: {
    projectMembers: number;
    timeEntries: number;
  };
}

interface CrewDetails {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  department?: string;
  phone?: string;
  avatar?: string;
  createdAt: string;
  projectMembers: Array<{
    id: string;
    role: string;
    department?: string;
    rate?: number;
    joinedAt: string;
    project: {
      id: string;
      title: string;
      status: string;
      type: string;
      startDate?: string;
      endDate?: string;
    };
  }>;
  timeEntries: Array<{
    id: string;
    date: string;
    totalHours?: number;
    status: string;
    project: {
      id: string;
      title: string;
    };
  }>;
}

const Crew: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');

  // Fetch crew members
  const { data: crewData, isLoading } = useQuery({
    queryKey: ['crew', { search: searchTerm, role: roleFilter, department: departmentFilter }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (roleFilter) params.append('role', roleFilter);
      if (departmentFilter) params.append('department', departmentFilter);

      const response = await fetch(`/api/crew?${params}`);
      if (!response.ok) throw new Error('Failed to fetch crew members');
      return response.json();
    },
  });

  // Fetch single crew member details if ID exists
  const { data: crewMemberData, isLoading: memberLoading } = useQuery({
    queryKey: ['crewMember', id],
    queryFn: async () => {
      if (!id) return null;
      const response = await fetch(`/api/crew/${id}`);
      if (!response.ok) throw new Error('Failed to fetch crew member');
      return response.json();
    },
    enabled: !!id,
  });

  // Fetch crew member summary
  const { data: summaryData } = useQuery({
    queryKey: ['crewSummary', id],
    queryFn: async () => {
      if (!id) return null;
      const response = await fetch(`/api/crew/${id}/summary`);
      if (!response.ok) throw new Error('Failed to fetch crew member summary');
      return response.json();
    },
    enabled: !!id,
  });

  const crewMembers = crewData?.users || [];
  const crewMember = crewMemberData;
  const summary = summaryData;

  const getRoleColor = (role: string) => {
    const colors: { [key: string]: string } = {
      ADMIN: 'bg-purple-100 text-purple-800',
      SUPERVISOR: 'bg-blue-100 text-blue-800',
      SUPERVISOR_USER: 'bg-indigo-100 text-indigo-800',
      CREW: 'bg-green-100 text-green-800',
      CLIENT: 'bg-gray-100 text-gray-800',
      GUEST: 'bg-yellow-100 text-yellow-800',
    };
    return colors[role] || 'bg-gray-100 text-gray-800';
  };

  if (id) {
    // Single crew member view
    if (memberLoading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      );
    }

    if (!crewMember) {
      return (
        <div className="text-center py-12">
          <UserGroupIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">Crew member not found</h3>
          <div className="mt-6">
            <button
              onClick={() => navigate('/crew')}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Back to Crew
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-white shadow-lg rounded-lg overflow-hidden">
          {/* Crew Member Header */}
          <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-6 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="h-16 w-16 rounded-full bg-white/20 flex items-center justify-center">
                  <span className="text-white text-2xl font-bold">
                    {crewMember.firstName[0]}{crewMember.lastName[0]}
                  </span>
                </div>
                <div className="ml-4">
                  <h1 className="text-3xl font-bold">
                    {crewMember.firstName} {crewMember.lastName}
                  </h1>
                  <p className="text-indigo-100">{crewMember.email}</p>
                  <div className="flex items-center space-x-4 mt-2">
                    <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getRoleColor(crewMember.role)}`}>
                      {crewMember.role.replace('_', ' ')}
                    </span>
                    {crewMember.department && (
                      <span className="text-sm text-indigo-100">
                        {crewMember.department}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={() => navigate('/crew')}
                className="px-4 py-2 bg-white/20 text-white rounded-md hover:bg-white/30"
              >
                Back to Crew
              </button>
            </div>
          </div>

          <div className="p-6">
            <div className="grid md:grid-cols-3 gap-6">
              {/* Main Content */}
              <div className="md:col-span-2 space-y-6">
                {/* Contact Information */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h3>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                    {crewMember.phone && (
                      <div className="flex items-center">
                        <PhoneIcon className="h-5 w-5 text-gray-400 mr-2" />
                        <span className="text-gray-700">{crewMember.phone}</span>
                      </div>
                    )}
                    <div className="flex items-center">
                      <EnvelopeIcon className="h-5 w-5 text-gray-400 mr-2" />
                      <span className="text-gray-700">{crewMember.email}</span>
                    </div>
                    <div className="flex items-center">
                      <CalendarIcon className="h-5 w-5 text-gray-400 mr-2" />
                      <span className="text-gray-700">
                        Joined {format(new Date(crewMember.createdAt), 'MMM d, yyyy')}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Project Assignments */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Project Assignments</h3>
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Project
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Role
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Department
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Rate
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              Joined
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {crewMember.projectMembers?.map((assignment) => (
                            <tr key={assignment.id}>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <div>
                                  <div className="text-sm font-medium text-gray-900">
                                    {assignment.project.title}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {assignment.project.type.replace('_', ' ')} • {assignment.project.status.replace('_', ' ')}
                                  </div>
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {assignment.role}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {assignment.department || '-'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {assignment.rate ? `$${assignment.rate}/day` : '-'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {format(new Date(assignment.joinedAt), 'MMM d, yyyy')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Recent Time Entries */}
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Time Entries</h3>
                  <div className="space-y-3">
                    {crewMember.timeEntries?.slice(0, 10).map((entry) => (
                      <div key={entry.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {entry.project.title}
                          </div>
                          <div className="text-xs text-gray-500">
                            {format(new Date(entry.date), 'MMM d, yyyy')}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold text-gray-900">
                            {entry.totalHours?.toFixed(1) || 0} hrs
                          </div>
                          <div className={`text-xs px-2 py-1 rounded-full inline-block ${
                            entry.status === 'APPROVED'
                              ? 'bg-green-100 text-green-800'
                              : entry.status === 'SUBMITTED'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {entry.status}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Sidebar */}
              <div className="space-y-6">
                {/* Quick Stats */}
                {summary && (
                  <div className="bg-blue-50 rounded-lg p-4">
                    <h3 className="text-lg font-semibold text-blue-900 mb-4">Time Summary</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-blue-700">Total Hours:</span>
                        <span className="font-semibold text-blue-900">
                          {summary.hours.total.toFixed(1)} hrs
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-blue-700">Overtime:</span>
                        <span className="font-semibold text-blue-900">
                          {summary.hours.overtime.toFixed(1)} hrs
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-blue-700">Total Pay:</span>
                        <span className="font-semibold text-blue-900">
                          ${summary.pay.total.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-blue-700">Projects:</span>
                        <span className="font-semibold text-blue-900">
                          {summary.projects.length}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Projects Worked On */}
                {summary?.projects && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Projects Worked On</h3>
                    <div className="space-y-2">
                      {summary.projects.map((project: any) => (
                        <div
                          key={project.id}
                          className="flex items-center justify-between p-2 bg-gray-50 rounded cursor-pointer hover:bg-gray-100"
                          onClick={() => navigate(`/projects/${project.id}`)}
                        >
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {project.title}
                            </div>
                            <div className="text-xs text-gray-500">{project.status}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Crew list view
  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Crew Management</h1>
            <p className="text-gray-600 mt-2">Manage your film production team members</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid md:grid-cols-4 gap-4">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search crew members..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Roles</option>
            <option value="ADMIN">Admin</option>
            <option value="SUPERVISOR">Supervisor</option>
            <option value="SUPERVISOR_USER">Supervisor User</option>
            <option value="CREW">Crew</option>
            <option value="CLIENT">Client</option>
            <option value="GUEST">Guest</option>
          </select>
          <input
            type="text"
            placeholder="Department..."
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={() => {
              setSearchTerm('');
              setRoleFilter('');
              setDepartmentFilter('');
            }}
            className="px-4 py-2 text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Crew Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {crewMembers.map((member: CrewMember) => (
            <div
              key={member.id}
              className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => navigate(`/crew/${member.id}`)}
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="h-12 w-12 rounded-full bg-indigo-500 flex items-center justify-center">
                    <span className="text-white text-lg font-bold">
                      {member.firstName[0]}{member.lastName[0]}
                    </span>
                  </div>
                  <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRoleColor(member.role)}`}>
                    {member.role.replace('_', ' ')}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  {member.firstName} {member.lastName}
                </h3>
                <p className="text-gray-600 text-sm mb-4">{member.email}</p>
                {member.department && (
                  <p className="text-gray-500 text-sm mb-4">
                    <BuildingOfficeIcon className="inline h-4 w-4 mr-1" />
                    {member.department}
                  </p>
                )}
                <div className="space-y-2 text-sm text-gray-500">
                  <div className="flex justify-between">
                    <span>Projects:</span>
                    <span>{member._count.projectMembers}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Time Entries:</span>
                    <span>{member._count.timeEntries}</span>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Joined {format(new Date(member.createdAt), 'MMM d, yyyy')}</span>
                    <span className="text-indigo-600">View Details →</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {crewMembers.length === 0 && !isLoading && (
        <div className="text-center py-12">
          <UserGroupIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No crew members found</h3>
          <p className="mt-1 text-sm text-gray-500">Try adjusting your search criteria.</p>
        </div>
      )}
    </div>
  );
};

export default Crew;