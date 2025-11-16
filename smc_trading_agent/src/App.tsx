import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import TradingInterface from "@/pages/TradingInterface";
import Analytics from "@/pages/Analytics";
import Configuration from "@/pages/Configuration";
import Monitoring from "@/pages/Monitoring";
import RiskManagement from "@/pages/RiskManagement";
import Reports from "@/pages/Reports";
import Login from "@/pages/Login";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="trading" element={<TradingInterface />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="config" element={<Configuration />} />
          <Route path="monitoring" element={<Monitoring />} />
          <Route path="risk" element={<RiskManagement />} />
          <Route path="reports" element={<Reports />} />
        </Route>
      </Routes>
    </Router>
  );
}
