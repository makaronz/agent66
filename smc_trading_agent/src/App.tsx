import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Toaster } from 'react-hot-toast';
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import TradingInterface from "@/pages/TradingInterface";
import Analytics from "@/pages/Analytics";
import Configuration from "@/pages/Configuration";
import Monitoring from "@/pages/Monitoring";
import Research from "@/pages/Research";
import RiskManagement from "@/pages/RiskManagement";
import Reports from "@/pages/Reports";
import Login from "@/pages/Login";
import MFASettings from "@/pages/MFASettings";
import AuthGuard from "@/components/auth/AuthGuard";
import SimpleAuthGuard from "@/components/auth/SimpleAuthGuard";
import { AuthProvider } from "@/contexts/AuthContext";

console.log('📱 App component loading...');

export default function App() {
  console.log('🔄 App component rendering...');
  
  try {
    return (
      <AuthProvider>
        <Router>
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
    );
  } catch (error) {
    console.error('❌ Error in App component:', error);
    throw error;
  }
}

console.log('✅ App component defined successfully');
