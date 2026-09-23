import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { DiscoveryProvider } from './context/DiscoveryContext';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { CompaniesPage } from './pages/CompaniesPage';
import { DiscoveryPage } from './pages/DiscoveryPage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <DiscoveryProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="jobs" element={<JobsPage />} />
                <Route path="opportunities" element={<Navigate to="/jobs" replace />} />
                <Route path="applications" element={<ApplicationsPage />} />
                <Route path="companies" element={<CompaniesPage />} />
                <Route path="discovery" element={<DiscoveryPage />} />
                <Route path="reports" element={<DiscoveryPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </DiscoveryProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;
