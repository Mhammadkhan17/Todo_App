'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/contexts/ThemeContext';
import LuxuryDashboardLayout from '@/components/layout/LuxuryDashboardLayout';
import { LuxuryCard, LuxuryCardContent } from '@/components/ui/LuxuryCard';
import { LuxuryButton } from '@/components/ui/LuxuryButton';
import CompactChatWidget from '@/components/chat/CompactChatWidget';
import { cn } from '@/lib/utils';

export default function SettingsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Show a loader while checking authentication to prevent hydration mismatch
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  // If not authenticated after loading, render nothing as redirect has already happened
  if (!isAuthenticated) {
    return null;
  }

  return (
    <LuxuryDashboardLayout
      user={user || null}
      onLogout={logout}
    >
      <div className="space-y-10">
        {/* Page Header */}
        <div className="flex flex-col gap-2 border-b border-stone-200 dark:border-stone-800 pb-8">
          <div className="flex items-center gap-2">
            <div className="w-1 h-1 bg-emerald-500 rounded-full" />
            <span className="text-[10px] font-mono font-bold text-stone-500 tracking-[0.3em] uppercase">Control_Center / Settings</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-stone-900 dark:text-white uppercase">System Configuration</h1>
          <p className="text-stone-500 text-xs font-light uppercase tracking-widest leading-relaxed">
            Manage your environment parameters and security credentials.
          </p>
        </div>

        {/* Settings Content */}
        <div className="grid grid-cols-1 gap-8">
          {/* Profile Settings */}
          <div className="space-y-4">
            <div className="flex items-center gap-3 px-2">
              <span className="text-[9px] font-mono text-stone-600 uppercase tracking-widest">Profile_Identity</span>
              <div className="h-px flex-1 bg-stone-200 dark:bg-stone-800" />
            </div>
            <LuxuryCard variant="default">
              <LuxuryCardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="block text-[10px] font-mono font-bold text-stone-500 uppercase tracking-widest">
                      Display_Name
                    </label>
                    <input
                      type="text"
                      aria-label="Display name"
                      defaultValue={user?.name || user?.email?.split('@')[0] || ''}
                      className="w-full px-4 py-2.5 bg-white dark:bg-[#141414] border border-stone-300 dark:border-stone-800 rounded-[4px] text-stone-900 dark:text-white text-sm focus:outline-none focus:border-emerald-600/60 transition-colors"
                      placeholder="identity_01"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="block text-[10px] font-mono font-bold text-stone-500 uppercase tracking-widest">
                      Security_Email
                    </label>
                    <input
                      type="email"
                      aria-label="Security email"
                      defaultValue={user?.email || ''}
                      className="w-full px-4 py-2.5 bg-stone-100 dark:bg-[#0a0a0a] border border-stone-200 dark:border-stone-900 rounded-[4px] text-stone-500 dark:text-stone-500 text-sm cursor-not-allowed opacity-60"
                      readOnly
                      disabled
                    />
                  </div>
                </div>
              </LuxuryCardContent>
            </LuxuryCard>
          </div>

          {/* Account Settings */}
          <div className="space-y-4">
            <div className="flex items-center gap-3 px-2">
              <span className="text-[9px] font-mono text-stone-600 uppercase tracking-widest">Environment_Parameters</span>
              <div className="h-px flex-1 bg-stone-200 dark:bg-stone-800" />
            </div>
            <LuxuryCard variant="default">
              <LuxuryCardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-4">
                    <label className="block text-[10px] font-mono font-bold text-stone-500 uppercase tracking-widest">
                      Visual_Protocol (Theme)
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {(['system', 'light', 'dark'] as const).map((t) => (
                        <button
                          key={t}
                          onClick={() => setTheme(t)}
                          className={cn(
                            "py-2.5 px-2 rounded-[4px] border text-[10px] font-mono uppercase tracking-widest transition-all duration-200",
                            theme === t
                              ? 'border-emerald-500 bg-emerald-500/10 text-emerald-600 dark:text-emerald-500'
                              : 'border-stone-300 dark:border-stone-800 bg-white dark:bg-[#141414] text-stone-600 dark:text-stone-500 hover:border-stone-400 dark:hover:border-stone-700 hover:text-stone-800 dark:hover:text-stone-300'
                          )}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <label className="block text-[10px] font-mono font-bold text-stone-500 uppercase tracking-widest">
                      Telemetry_Signals
                    </label>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-3 bg-white dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px]">
                        <span className="text-[10px] font-mono text-stone-600 dark:text-stone-300 uppercase tracking-tighter">Email_Alerts</span>
                        <div className="w-8 h-4 bg-emerald-500/20 border border-emerald-500/30 rounded-full relative flex items-center px-0.5">
                          <div className="w-3 h-3 bg-emerald-500 rounded-full translate-x-4" />
                        </div>
                      </div>
                      <div className="flex items-center justify-between p-3 bg-white dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px]">
                        <span className="text-[10px] font-mono text-stone-600 dark:text-stone-300 uppercase tracking-tighter">Push_Notifications</span>
                        <div className="w-8 h-4 bg-emerald-500/20 border border-emerald-500/30 rounded-full relative flex items-center px-0.5">
                          <div className="w-3 h-3 bg-emerald-500 rounded-full translate-x-4" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </LuxuryCardContent>
            </LuxuryCard>
          </div>

          {/* Danger Zone */}
          <div className="space-y-4">
            <div className="flex items-center gap-3 px-2">
              <span className="text-[9px] font-mono text-red-900 dark:text-red-400 uppercase tracking-widest">Destructive_Operations</span>
              <div className="h-px flex-1 bg-red-900/20" />
            </div>
            <LuxuryCard className="border-red-900/30 bg-red-950/5">
              <LuxuryCardContent>
                <div className="flex flex-col md:flex-row items-center justify-between gap-6 p-2">
                  <div className="space-y-1 text-center md:text-left">
                    <h3 className="text-xs font-mono font-bold text-red-500 tracking-[0.2em] uppercase">Terminate_Account</h3>
                    <p className="text-[10px] text-stone-600 font-light uppercase tracking-tighter">
                      Permanently purge all associated data and telemetry from the registry.
                    </p>
                  </div>
                  <button className="px-6 py-2.5 bg-red-600/10 border border-red-600/20 text-red-500 text-[10px] font-mono font-bold uppercase tracking-widest rounded-[4px] hover:bg-red-600 hover:text-white transition-all">
                    Execute Purge
                  </button>
                </div>
              </LuxuryCardContent>
            </LuxuryCard>
          </div>
        </div>

        {/* Global Action Matrix */}
        <div className="flex justify-end gap-4 pt-10 border-t border-stone-200 dark:border-stone-800">
          <LuxuryButton variant="outline" className="px-8">Reset_Changes</LuxuryButton>
          <LuxuryButton className="px-10">Commit_Configuration</LuxuryButton>
        </div>
      </div>
      <CompactChatWidget />
    </LuxuryDashboardLayout>
  );
}