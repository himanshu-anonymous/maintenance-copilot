import { ShieldAlert, Sun, Moon, Wrench, BarChart3, UserCheck, Activity } from 'lucide-react';
import { Role } from '../types';

interface NavbarProps {
  currentView: 'technician' | 'supervisor';
  onSelectView: (view: 'technician' | 'supervisor') => void;
  currentRole: Role;
  onSwitchRole: (role: Role) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  pendingApprovalsCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  onSelectView,
  currentRole,
  onSwitchRole,
  darkMode,
  onToggleDarkMode,
  pendingApprovalsCount,
}) => {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md shadow-sm">
      {/* Universal Synthetic Demo Notice Banner */}
      <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-1.5 text-center text-xs font-mono font-medium text-amber-700 dark:text-amber-400 flex items-center justify-center gap-2">
        <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 text-amber-500" />
        <span>Notice: Demo with synthetic data. Not for real safety decisions.</span>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-slate-900 dark:text-white text-base">
                Readiness Assistant
              </span>
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                Gemma 4
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 hidden sm:block">
              Evidence-Grounded Reliability Copilot
            </p>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center p-1 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
          <button
            onClick={() => onSelectView('technician')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              currentView === 'technician'
                ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Wrench className="w-3.5 h-3.5" />
            <span>Technician Copilot</span>
          </button>
          <button
            onClick={() => onSelectView('supervisor')}
            className={`relative flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              currentView === 'supervisor'
                ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Supervisor Dashboard</span>
            {pendingApprovalsCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center font-bold">
                {pendingApprovalsCount}
              </span>
            )}
          </button>
        </div>

        {/* User Role Switcher & Theme Toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 dark:bg-slate-800/80 rounded-lg border border-slate-200 dark:border-slate-700 text-xs">
            <UserCheck className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
            <select
              value={currentRole}
              onChange={(e) => onSwitchRole(e.target.value as Role)}
              className="bg-transparent font-medium text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer text-xs"
            >
              <option value="technician" className="dark:bg-slate-900">
                Alex Vance (Tech)
              </option>
              <option value="supervisor" className="dark:bg-slate-900">
                Elena Rostova (Supervisor)
              </option>
            </select>
          </div>

          <button
            onClick={onToggleDarkMode}
            aria-label="Toggle theme"
            className="p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
};
