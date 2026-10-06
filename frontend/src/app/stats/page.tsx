'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useTasks } from '@/hooks/useTasks';
import LuxuryDashboardLayout from '@/components/layout/LuxuryDashboardLayout';
import { LuxuryStatisticsCard } from '@/components/tasks/LuxuryStatisticsCard';
import CompactChatWidget from '@/components/chat/CompactChatWidget';

export default function StatsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth(); // Get auth loading state
  const { statistics, isLoading: statsLoading } = useTasks();

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
      user={user || null} // Handle case where user might be null
      onLogout={logout}
    >
      <div className="space-y-6">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold uppercase text-stone-900 dark:text-white">Task Analytics</h1>
          <p className="text-stone-600 dark:text-stone-400 mt-1 text-sm sm:text-base">
            Detailed insights and statistics about your task management
          </p>
        </div>

        {/* Statistics */}
        {statistics && <LuxuryStatisticsCard stats={statistics} />}

        {/* Additional Analytics */}
        {!statsLoading && !statistics && (
          <div className="text-center py-12">
            <div className="text-stone-500 dark:text-stone-400">
              <svg className="mx-auto h-12 w-12 text-stone-400 dark:text-stone-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-stone-900 dark:text-white">No data available</h3>
              <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">
                Create some tasks to see analytics and statistics.
              </p>
            </div>
          </div>
        )}

        {statsLoading && (
          <div className="text-center py-12">
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
            </div>
            <p className="mt-4 text-stone-600 dark:text-stone-400">Loading statistics...</p>
          </div>
        )}
      </div>
      <CompactChatWidget />
    </LuxuryDashboardLayout>
  );
}