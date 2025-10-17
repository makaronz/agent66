import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChartBarIcon,
  CalendarIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
  ClockIcon,
  FunnelIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface TimeSummaryData {
  summary: Array<{
    [key: string]: any;
    user?: { id: string; firstName: string; lastName: string };
    project?: { id: string; title: string };
  }>;
  totals: {
    totalHours: number;
    overtimeHours: number;
    totalPay: number;
    totalEntries: number;
  };
}

interface CostAnalysisData {
  totalCost: number;
  totalEntries: number;
  costByDepartment: { [key: string]: number };
  costByRole: { [key: string]: number };
  costByProject: Array<{
    projectId: string;
    projectTitle?: string;
    cost: number;
  }>;
  overtimeCost: {
    total: number;
    hours: number;
  };
}

const Reports: React.FC = () => {
  const [reportType, setReportType] = useState('time-summary');
  const [timeRange, setTimeRange] = useState('month');
  const [groupBy, setGroupBy] = useState('day');
  const [selectedProject, setSelectedProject] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Fetch time summary data
  const { data: timeSummaryData, isLoading: timeLoading } = useQuery({
    queryKey: ['timeSummary', { groupBy, startDate, endDate, projectId: selectedProject }],
    queryFn: async () => {
      const params = new URLSearchParams({ groupBy });
      if (startDate) params.append('startDate', startDate);
      if (endDate) params.append('endDate', endDate);
      if (selectedProject) params.append('projectId', selectedProject);

      const response = await fetch(`/api/reports/time-summary?${params}`);
      if (!response.ok) throw new Error('Failed to fetch time summary');
      return response.json();
    },
    enabled: reportType === 'time-summary',
  });

  // Fetch cost analysis data
  const { data: costAnalysisData, isLoading: costLoading } = useQuery({
    queryKey: ['costAnalysis', { startDate, endDate, projectId: selectedProject }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (startDate) params.append('startDate', startDate);
      if (endDate) params.append('endDate', endDate);
      if (selectedProject) params.append('projectId', selectedProject);

      const response = await fetch(`/api/reports/cost-analysis?${params}`);
      if (!response.ok) throw new Error('Failed to fetch cost analysis');
      return response.json();
    },
    enabled: reportType === 'cost-analysis',
  });

  // Fetch projects for filter
  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await fetch('/api/projects');
      if (!response.ok) throw new Error('Failed to fetch projects');
      return response.json();
    },
  });

  const timeSummary = timeSummaryData as TimeSummaryData;
  const costAnalysis = costAnalysisData as CostAnalysisData;
  const projects = projectsData?.projects || [];

  // Prepare chart data
  const timeChartData = timeSummary?.summary?.map(item => ({
    name: item.user ? `${item.user.firstName} ${item.user.lastName}` :
          item.project ? item.project.title : 'Unknown',
    hours: item._sum.totalHours || 0,
    overtime: item._sum.overtimeHours || 0,
    entries: item._count.id,
  })) || [];

  const costByDepartmentData = Object.entries(costAnalysis?.costByDepartment || {})
    .map(([department, cost]) => ({ name: department, value: cost }));

  const costByRoleData = Object.entries(costAnalysis?.costByRole || {})
    .map(([role, cost]) => ({ name: role.replace('_', ' '), value: cost }));

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'];

  const handleExportReport = async () => {
    try {
      const params = new URLSearchParams();
      if (reportType === 'time-summary') {
        params.append('type', 'TIME_SUMMARY');
      } else if (reportType === 'cost-analysis') {
        params.append('type', 'COST_ANALYSIS');
      }
      if (startDate) params.append('startDate', startDate);
      if (endDate) params.append('endDate', endDate);
      if (selectedProject) params.append('projectId', selectedProject);

      const response = await fetch(`/api/reports/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: reportType === 'time-summary' ? 'TIME_SUMMARY' : 'COST_ANALYSIS',
          title: `${reportType === 'time-summary' ? 'Time Summary' : 'Cost Analysis'} Report`,
          description: `Generated on ${new Date().toLocaleDateString()}`,
          data: reportType === 'time-summary' ? timeSummary : costAnalysis,
          filters: { startDate, endDate, project: selectedProject, groupBy },
        }),
      });

      if (response.ok) {
        // Here you could trigger a download or show a success message
        console.log('Report saved successfully');
      }
    } catch (error) {
      console.error('Failed to save report:', error);
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Reports & Analytics</h1>
            <p className="text-gray-600 mt-2">Track time, costs, and project performance</p>
          </div>
          <button
            onClick={handleExportReport}
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700"
          >
            <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
            Export Report
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <div className="grid md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="time-summary">Time Summary</option>
              <option value="cost-analysis">Cost Analysis</option>
              <option value="project-progress">Project Progress</option>
              <option value="payroll">Payroll Report</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Project</label>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Projects</option>
              {projects.map((project: any) => (
                <option key={project.id} value={project.id}>
                  {project.title}
                </option>
              ))}
            </select>
          </div>

          {reportType === 'time-summary' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Group By</label>
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="day">Day</option>
                <option value="week">Week</option>
                <option value="month">Month</option>
                <option value="user">User</option>
                <option value="project">Project</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Report Content */}
      {reportType === 'time-summary' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid md:grid-cols-4 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-3 bg-blue-100 rounded-full">
                  <ClockIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Hours</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {timeSummary?.totals.totalHours.toFixed(1) || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-3 bg-yellow-100 rounded-full">
                  <ClockIcon className="h-6 w-6 text-yellow-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Overtime Hours</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {timeSummary?.totals.overtimeHours.toFixed(1) || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-3 bg-green-100 rounded-full">
                  <DocumentTextIcon className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Entries</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {timeSummary?.totals.totalEntries || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-3 bg-purple-100 rounded-full">
                  <CurrencyDollarIcon className="h-6 w-6 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${timeSummary?.totals.totalPay.toFixed(2) || 0}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Time Chart */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hours Breakdown</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={timeChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="hours" fill="#3B82F6" name="Regular Hours" />
                <Bar dataKey="overtime" fill="#F59E0B" name="Overtime Hours" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {reportType === 'cost-analysis' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-3 bg-green-100 rounded-full">
                  <CurrencyDollarIcon className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${costAnalysis?.totalCost.toFixed(2) || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-3 bg-yellow-100 rounded-full">
                  <ClockIcon className="h-6 w-6 text-yellow-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Overtime Cost</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ${costAnalysis?.overtimeCost.total.toFixed(2) || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-3 bg-blue-100 rounded-full">
                  <DocumentTextIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm text-gray-500">Total Entries</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {costAnalysis?.totalEntries || 0}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Cost Charts */}
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost by Department</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={costByDepartmentData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {costByDepartmentData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost by Role</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={costByRoleData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#10B981" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Project Costs */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost by Project</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Project
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total Cost
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {costAnalysis?.costByProject?.map((project) => (
                    <tr key={project.projectId}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {project.projectTitle || 'Unknown Project'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${project.cost.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Placeholder for other report types */}
      {(reportType === 'project-progress' || reportType === 'payroll') && (
        <div className="bg-white p-8 rounded-lg shadow text-center">
          <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            {reportType === 'project-progress' ? 'Project Progress' : 'Payroll'} Reports
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            This report type is coming soon.
          </p>
        </div>
      )}
    </div>
  );
};

export default Reports;