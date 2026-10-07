'use client';

import { User } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  ClipboardList,
  Settings,
  User as UserIcon,
  LogOut,
  Menu,
  X,
  Moon,
  Sun,
  ShieldCheck,
  BarChart3,
  MessageSquare,
  Terminal
} from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';

interface LuxuryDashboardLayoutProps {
  user: User | null;
  children: React.ReactNode;
  onLogout: () => void;
  // Immersive = no top navbar, no footer, no main padding/max-width — the page
  // owns the entire right column (used by /chat for an edge-to-edge chat).
  immersive?: boolean;
}

export default function LuxuryDashboardLayout({ user, children, onLogout, immersive = false }: LuxuryDashboardLayoutProps) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  // Pages without the top navbar (which hosts the hamburger) can open the
  // sidebar by dispatching this event from their own header.
  useEffect(() => {
    const openNav = () => setSidebarOpen(true);
    window.addEventListener('app:open-nav', openNav);
    return () => window.removeEventListener('app:open-nav', openNav);
  }, []);

  // Resolve the effective theme after mount to avoid a hydration mismatch
  const [resolvedDark, setResolvedDark] = useState(false);
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => setResolvedDark(theme === 'dark' || (theme === 'system' && media.matches));
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [theme]);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Tasks', href: '/tasks', icon: ClipboardList },
    { name: 'Stats', href: '/stats', icon: BarChart3 },
    { name: 'Chat', href: '/chat', icon: MessageSquare },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-stone-50 dark:bg-[#0a0a0a] text-stone-900 dark:text-[#fafaf9] selection:bg-emerald-500/30 font-sans transition-colors duration-300">
      {/* Structural Grid Background */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,var(--grid-line)_1px,transparent_1px),linear-gradient(to_bottom,var(--grid-line)_1px,transparent_1px)] bg-[size:40px_40px] opacity-[0.15] pointer-events-none"></div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 lg:hidden bg-black/60 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar - Monolith Architecture */}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-[#0f0f0f] border-r border-stone-200 dark:border-stone-800 transition-transform duration-300 ease-[0.25,1,0.5,1] lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex flex-col h-full">
          {/* Sidebar Header */}
          <div className="h-16 flex items-center justify-between px-6 border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#141414]">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 bg-emerald-500 flex items-center justify-center rounded-[4px]">
                <ShieldCheck className="w-4 h-4 text-[#0a0a0a]" />
              </div>
              <span className="font-bold tracking-tight text-sm text-stone-900 dark:text-white">TodoFlow<span className="text-emerald-500">.</span></span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              aria-label="Close navigation"
              className="lg:hidden p-2 -m-1 text-stone-500 hover:text-stone-900 dark:hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
            <div className="px-3 mb-4">
              <p className="text-[11px] font-mono font-bold uppercase tracking-widest text-stone-500 dark:text-stone-500">Operations</p>
            </div>
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <a
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-[4px] text-sm transition-all duration-200 group relative",
                    isActive 
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20" 
                      : "text-stone-500 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-800 hover:text-stone-900 dark:hover:text-stone-200 border border-transparent"
                  )}
                >
                  <item.icon className={cn("w-4 h-4", isActive ? "text-emerald-600 dark:text-emerald-400" : "text-stone-400 dark:text-stone-500 group-hover:text-stone-600 dark:group-hover:text-stone-300")} />
                  <span className="font-medium">{item.name}</span>
                  {isActive && (
                    <motion.div layoutId="active-nav" className="absolute left-0 w-1 h-4 bg-emerald-500 rounded-r-full" />
                  )}
                </a>
              );
            })}
          </nav>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-stone-200 dark:border-stone-800 bg-stone-50/50 dark:bg-[#141414]/50">
            <div className="flex items-center gap-3 p-2 bg-white dark:bg-stone-900/50 rounded-[4px] border border-stone-200 dark:border-stone-800 mb-4">
              <div className="w-8 h-8 rounded-[4px] bg-stone-100 dark:bg-stone-800 flex items-center justify-center">
                <UserIcon className="w-4 h-4 text-stone-400 dark:text-stone-500" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold truncate text-stone-900 dark:text-stone-200">{user?.username || user?.name || 'User'}</p>
                <p className="text-[11px] font-mono font-medium text-stone-500 dark:text-stone-500 uppercase tracking-tighter truncate">Verified Session</p>
              </div>
            </div>
            <button
              onClick={onLogout}
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-[4px] text-[11px] font-mono font-bold uppercase tracking-widest text-stone-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-500/5 transition-all"
            >
              <LogOut className="w-3.5 h-3.5" />
              Terminate
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="lg:pl-64 flex flex-col min-h-screen relative z-10">
        {/* Top Header */}
        {!immersive && (
          <header className="h-16 flex items-center justify-between px-6 border-b border-stone-200 dark:border-stone-800 bg-stone-50/80 dark:bg-[#0a0a0a]/80 backdrop-blur-md sticky top-0 z-30">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(true)}
                aria-label="Open navigation"
                className="lg:hidden p-2 -m-1 text-stone-500 hover:text-stone-900 dark:hover:text-white"
              >
                <Menu className="w-5 h-5" />
              </button>
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-600 dark:text-emerald-500" />
                <h1 className="text-[11px] font-mono font-bold uppercase tracking-widest text-stone-500 dark:text-stone-400">
                  {pathname.split('/').pop() || 'Core'} {'//'} Execution Mode
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={toggleTheme}
                aria-label={resolvedDark ? 'Switch to light theme' : 'Switch to dark theme'}
                className="min-h-11 min-w-11 flex items-center justify-center text-stone-500 hover:text-stone-900 dark:hover:text-white transition-colors"
              >
                {resolvedDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </button>
            </div>
          </header>
        )}

        {/* Content Section */}
        <main
          className={
            immersive
              ? 'flex-1 w-full'
              : 'flex-1 p-6 lg:p-10 max-w-screen-2xl mx-auto w-full'
          }
        >
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: [0.25, 1, 0.5, 1] }}
          >
            {children}
          </motion.div>
        </main>

        {/* Technical Footer */}
        {!immersive && (
          <footer className="py-6 px-6 lg:px-10 border-t border-stone-200 dark:border-stone-900 bg-stone-50 dark:bg-[#0a0a0a] flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-[11px] font-mono font-medium text-stone-500 dark:text-stone-500 uppercase tracking-widest">&copy; 2026 TodoFlow</p>
            <div className="flex items-center gap-1.5 text-[11px] font-mono font-medium text-stone-500 dark:text-stone-500">
              <span className="w-1 h-1 bg-emerald-500 rounded-full"></span>
              Systems Locked
            </div>
          </footer>
        )}
      </div>
    </div>
  );
}


