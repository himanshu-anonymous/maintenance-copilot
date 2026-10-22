import { ShieldAlert, Sun, Moon, Wrench, LayoutDashboard, UserCheck, Activity } from 'lucide-react';
import { Role } from '../types';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

interface NavbarProps {
  currentView: 'technician' | 'supervisor';
  onSelectView: (view: 'technician' | 'supervisor') => void;
  currentRole: Role;
  onSwitchRole: (role: Role) => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  pendingApprovalsCount: number;
}

export const Navbar = ({
  currentView,
  onSelectView,
  currentRole,
  onSwitchRole,
  darkMode,
  onToggleDarkMode,
  pendingApprovalsCount,
}: NavbarProps) => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-zinc-200 dark:border-zinc-800 bg-white/95 dark:bg-zinc-950/95 backdrop-blur-md supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-zinc-950/60">
      {/* Notice Banner */}
      <div className="border-b border-zinc-200/80 dark:border-zinc-800/80 bg-zinc-50 dark:bg-zinc-900/60 px-4 py-1.5 text-center text-xs font-mono font-medium text-zinc-600 dark:text-zinc-400 flex items-center justify-center gap-2">
        <ShieldAlert className="w-3.5 h-3.5 text-amber-500 shrink-0" />
        <span>Demo with synthetic data. Not for real safety decisions.</span>
      </div>

      <div className="max-w-7xl mx-auto flex h-14 items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo & Brand */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900 text-zinc-50 dark:bg-zinc-50 dark:text-zinc-900 shadow-xs">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
                Readiness Assistant
              </span>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-mono">
                Gemma 4
              </Badge>
            </div>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 hidden sm:block">
              Industrial Rotating Machinery Reliability Copilot
            </p>
          </div>
        </div>

        {/* View Switcher Pills */}
        <div className="flex items-center rounded-lg bg-zinc-100 p-0.5 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700">
          <button
            type="button"
            onClick={() => onSelectView('technician')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-all ${
              currentView === 'technician'
                ? 'bg-white text-zinc-900 shadow-xs dark:bg-zinc-950 dark:text-zinc-50 font-semibold'
                : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50'
            }`}
          >
            <Wrench className="h-3.5 w-3.5" />
            <span>Technician Copilot</span>
          </button>
          <button
            type="button"
            onClick={() => onSelectView('supervisor')}
            className={`relative flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-all ${
              currentView === 'supervisor'
                ? 'bg-white text-zinc-900 shadow-xs dark:bg-zinc-950 dark:text-zinc-50 font-semibold'
                : 'text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50'
            }`}
          >
            <LayoutDashboard className="h-3.5 w-3.5" />
            <span>Supervisor Board</span>
            {pendingApprovalsCount > 0 && (
              <span className="flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                {pendingApprovalsCount}
              </span>
            )}
          </button>
        </div>

        {/* User Role & Dark Mode Toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-2 py-1 text-xs">
            <UserCheck className="h-3.5 w-3.5 text-zinc-500" />
            <select
              value={currentRole}
              onChange={(e) => onSwitchRole(e.target.value as Role)}
              className="bg-transparent font-medium text-zinc-800 dark:text-zinc-200 focus:outline-none cursor-pointer text-xs"
            >
              <option value="technician" className="dark:bg-zinc-900">
                Alex Vance (Tech)
              </option>
              <option value="supervisor" className="dark:bg-zinc-900">
                Elena Rostova (Supervisor)
              </option>
            </select>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleDarkMode}
            aria-label="Toggle theme"
            className="h-8 w-8 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </header>
  );
};
