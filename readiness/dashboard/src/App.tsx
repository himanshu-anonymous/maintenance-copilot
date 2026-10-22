import { useState, useEffect } from 'react';
import { Role, Asset } from './types';
import { Navbar } from './components/Navbar';
import { TechnicianView } from './components/TechnicianView';
import { SupervisorDashboard } from './components/SupervisorDashboard';
import { loginUser, fetchAssets, fetchWorkOrders } from './api';

export default function App() {
  const [currentView, setCurrentView] = useState<'technician' | 'supervisor'>('technician');
  const [currentRole, setCurrentRole] = useState<Role>('technician');
  const [darkMode, setDarkMode] = useState<boolean>(true);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);

  // Initialize theme class
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Authenticate user on role switch & load global data
  const syncUserAndData = async (role: Role) => {
    try {
      if (role === 'technician') {
        await loginUser('tech', 'tech123');
      } else {
        await loginUser('supervisor', 'super123');
      }

      const [assetsData, wosData] = await Promise.all([
        fetchAssets(),
        fetchWorkOrders('pending_approval'),
      ]);
      setAssets(assetsData || []);
      setPendingApprovalsCount(wosData ? wosData.length : 0);
    } catch (e) {
      console.warn('Initial auth sync warning', e);
    }
  };

  useEffect(() => {
    syncUserAndData(currentRole);
  }, [currentRole]);

  const handleSwitchRole = (role: Role) => {
    setCurrentRole(role);
    if (role === 'supervisor') {
      setCurrentView('supervisor');
    } else {
      setCurrentView('technician');
    }
  };

  const handleRefreshData = async () => {
    try {
      const [assetsData, wosData] = await Promise.all([
        fetchAssets(),
        fetchWorkOrders('pending_approval'),
      ]);
      setAssets(assetsData || []);
      setPendingApprovalsCount(wosData ? wosData.length : 0);
    } catch (e) {
      console.warn('Refresh error', e);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors duration-200">
      <Navbar
        currentView={currentView}
        onSelectView={setCurrentView}
        currentRole={currentRole}
        onSwitchRole={handleSwitchRole}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
        pendingApprovalsCount={pendingApprovalsCount}
      />

      <main className="flex-1 pb-16">
        {currentView === 'technician' ? (
          <TechnicianView
            assets={assets}
            onWorkOrderSubmitted={handleRefreshData}
          />
        ) : (
          <SupervisorDashboard onRefreshData={handleRefreshData} />
        )}
      </main>

      <footer className="border-t border-slate-200 dark:border-slate-800/80 py-6 px-4 bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm text-center text-xs text-slate-500 space-y-1">
        <p className="font-semibold text-slate-700 dark:text-slate-300">
          Readiness Assistant • Equipment Troubleshooting & Reliability Copilot
        </p>
        <p className="font-mono text-[11px] text-amber-600 dark:text-amber-400">
          Demo with synthetic data. Not for real safety decisions.
        </p>
        <p className="text-[11px] text-slate-400">
          Graph decides • Gemma 4 explains • In-memory JsonGraphStore (0.77ms) • SQLite Operational Memory
        </p>
      </footer>
    </div>
  );
}
