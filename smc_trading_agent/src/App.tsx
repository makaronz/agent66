import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Toaster } from 'react-hot-toast';
import Layout from "@/components/Layout";
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const TradingInterface = lazy(() => import("@/pages/TradingInterface"));
const Analytics = lazy(() => import("@/pages/Analytics"));
const Configuration = lazy(() => import("@/pages/Configuration"));
const Monitoring = lazy(() => import("@/pages/Monitoring"));
const Research = lazy(() => import("@/pages/Research"));
const RiskManagement = lazy(() => import("@/pages/RiskManagement"));
const Reports = lazy(() => import("@/pages/Reports"));
const Login = lazy(() => import("@/pages/Login"));
const MFASettings = lazy(() => import("@/pages/MFASettings"));
import AuthGuard from "@/components/auth/AuthGuard";
import SimpleAuthGuard from "@/components/auth/SimpleAuthGuard";
import { AuthProvider } from "@/contexts/AuthContext";
import { QueryProvider } from "@/providers/QueryProvider";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import WebVitalsProvider from "@/components/WebVitalsProvider";
import { HelmetProvider } from 'react-helmet-async';

console.log('📱 App component loading...');

export default function App() {
  console.log('🔄 App component rendering...');
  
  try {
    return (
      <HelmetProvider>
        <WebVitalsProvider 
          enabled={process.env.NODE_ENV === 'production'}
          endpoint="/api/analytics/vitals"
          batchSize={5}
          flushInterval={30000}
        >
          <QueryProvider>
            <AuthProvider>
        <Router>
          <Suspense fallback={<div className="p-8 flex items-center justify-center"><LoadingSpinner /></div>}>
          <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          
          {/* Protected routes */}
          <Route path="/" element={
            <AuthGuard>
              <Layout />
            </AuthGuard>
          }>
            <Route index element={<Dashboard />} />
            <Route path="trading" element={<TradingInterface />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="config" element={<Configuration />} />
            <Route path="monitoring" element={<Monitoring />} />
            <Route path="research" element={<Research />} />
            <Route path="risk" element={<RiskManagement />} />
            <Route path="reports" element={<Reports />} />
            <Route path="mfa" element={<MFASettings />} />
          </Route>
          </Routes>
          </Suspense>
          <Toaster 
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#4ade80',
                secondary: '#fff',
              },
            },
            error: {
              duration: 4000,
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />

        </Router>
          </AuthProvider>
            </QueryProvider>
        </WebVitalsProvider>
      </HelmetProvider>
    );
  } catch (error) {
    console.error('❌ Error in App component:', error);
    throw error;
  }
}

console.log('✅ App component defined successfully');
