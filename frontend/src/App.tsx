import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider } from 'react-redux';
import { Toaster } from 'react-hot-toast';
import { store } from './store/store';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import Dashboard from './components/Dashboard';
import PrivateRoute from './components/PrivateRoute';
import TimeClock from './components/TimeClock';
import Projects from './components/Projects';
import Crew from './components/Crew';
import Reports from './components/Reports';
import Layout from './components/Layout';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <Router>
          <Toaster position="top-right" />
          <div className="App min-h-screen bg-gray-50">
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<LoginForm />} />
              <Route path="/register" element={<RegisterForm />} />

              {/* Protected routes */}
              <Route path="/" element={<PrivateRoute />}>
                <Route element={<Layout />}>
                  <Route index element={<Dashboard />} />
                  <Route path="/time-clock" element={<TimeClock />} />
                  <Route path="/projects" element={<Projects />} />
                  <Route path="/projects/:id" element={<Projects />} />
                  <Route path="/crew" element={<Crew />} />
                  <Route path="/crew/:id" element={<Crew />} />
                  <Route path="/reports" element={<Reports />} />
                </Route>
              </Route>
            </Routes>
          </div>
        </Router>
      </QueryClientProvider>
    </Provider>
  );
}

export default App;