'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useTasks } from '@/hooks/useTasks';
import LuxuryDashboardLayout from '@/components/layout/LuxuryDashboardLayout';
import { LuxuryTaskList } from '@/components/tasks/LuxuryTaskList';
import { LuxuryStatisticsCard } from '@/components/tasks/LuxuryStatisticsCard';
import { LuxuryTaskForm } from '@/components/tasks/LuxuryTaskForm';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  FunnelIcon,
  XMarkIcon,
  CheckCircleIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';
import { Terminal } from 'lucide-react';
import { Task, CreateTaskData } from '@/types';
import { TaskFilter } from '@/components/tasks/TaskFilter';
import { cn } from '@/lib/utils';
import {
  LuxuryCard,
  LuxuryCardContent
} from '@/components/ui/LuxuryCard';
import { LuxuryButton } from '@/components/ui/LuxuryButton';
import CompactChatWidget from '@/components/chat/CompactChatWidget';
import { formatDistanceToNow } from 'date-fns';

interface ActivityItem {
  id: string;
  type: 'created' | 'completed' | 'updated';
  taskTitle: string;
  timestamp: string;
}

export default function EnhancedDashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const { tasks, statistics, isLoading: tasksLoading, createTask, toggleTask, deleteTask, fetchTasks, fetchStatistics } = useTasks();
  
  // Derive recent activities from tasks
  const recentActivities: ActivityItem[] = Array.isArray(tasks) 
    ? [...tasks]
        .flatMap(task => {
          const activities: ActivityItem[] = [];
          
          // Creation activity
          activities.push({
            id: `create-${task.id}`,
            type: 'created',
            taskTitle: task.title,
            timestamp: task.created_at
          });
          
          // Completion activity
          if (task.completed && task.updated_at) {
            activities.push({
              id: `complete-${task.id}`,
              type: 'completed',
              taskTitle: task.title,
              timestamp: task.updated_at
            });
          }
          
          return activities;
        })
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        .slice(0, 5)
    : [];

  const [showTaskForm, setShowTaskForm] = useState(false);
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'pending' | 'completed'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'created_at' | 'due_date' | 'priority'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Redirect to login if not authenticated (consolidated redirect logic)
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Fetch tasks and statistics when user becomes available
  useEffect(() => {
    if (user && isAuthenticated) {
      fetchTasks(user.id);
      fetchStatistics(user.id);
    }
  }, [user, isAuthenticated, fetchTasks, fetchStatistics]);

  // Additional effect to ensure data is fresh when component mounts
  useEffect(() => {
    if (user && isAuthenticated) {
      const timer = setTimeout(() => {
        fetchTasks(user.id);
      }, 100); // Small delay to ensure auth is fully ready

      return () => clearTimeout(timer);
    }
  }, [user, isAuthenticated, fetchTasks]);

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

  const filteredAndSortedTasks = Array.isArray(tasks) ?
    tasks
      .filter(task => {
        if (activeTab === 'pending') return !task.completed;
        if (activeTab === 'completed') return task.completed;
        return true;
      })
      .filter(task =>
        task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (task.description && task.description.toLowerCase().includes(searchTerm.toLowerCase()))
      )
      .sort((a, b) => {
        const aValue = a[sortBy] as string | number | undefined;
        const bValue = b[sortBy] as string | number | undefined;

        if (sortBy === 'due_date') {
          const aTime = aValue ? new Date(aValue as string).getTime() : (sortOrder === 'asc' ? Infinity : -Infinity);
          const bTime = bValue ? new Date(bValue as string).getTime() : (sortOrder === 'asc' ? Infinity : -Infinity);
          return sortOrder === 'asc' ? aTime - bTime : bTime - aTime;
        }

        if (typeof aValue === 'string' && typeof bValue === 'string') {
          const aStr = aValue.toLowerCase();
          const bStr = bValue.toLowerCase();
          if (sortOrder === 'asc') {
            return aStr.localeCompare(bStr);
          } else {
            return bStr.localeCompare(aStr);
          }
        }

        const aNum = (aValue ?? 0) as number;
        const bNum = (bValue ?? 0) as number;

        if (sortOrder === 'asc') {
          return aNum < bNum ? -1 : aNum > bNum ? 1 : 0;
        } else {
          return aNum > bNum ? -1 : aNum < bNum ? 1 : 0;
        }
      })
    : [];

  const handleCreateTask = async (data: CreateTaskData) => {
    try {
      setIsCreatingTask(true);
      await createTask(user!.id, data);
      setShowTaskForm(false);
    } catch {
      // Error is handled in the hook
    } finally {
      setIsCreatingTask(false);
    }
  };

  const handleTaskAction = (action: 'toggle' | 'edit' | 'delete', task: Task) => {
    switch (action) {
      case 'toggle':
        toggleTask(user!.id, task.id);
        break;
      case 'edit':
        // TODO: Implement edit functionality
        console.log('Edit task:', task);
        break;
      case 'delete':
        deleteTask(user!.id, task.id);
        break;
    }
  };

  const tabs: { id: 'all' | 'pending' | 'completed'; name: string; count: number }[] = [
    { id: 'all', name: 'All Tasks', count: Array.isArray(tasks) ? tasks.length : 0 },
    { id: 'pending', name: 'Pending', count: Array.isArray(tasks) ? tasks.filter(t => !t.completed).length : 0 },
    { id: 'completed', name: 'Completed', count: Array.isArray(tasks) ? tasks.filter(t => t.completed).length : 0 },
  ];

  return (
    <LuxuryDashboardLayout
      user={user || null}
      onLogout={logout}
    >
      {/* Header with technical breadcrumb */}
      <div className="mb-10">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 mb-8 border-b border-stone-200 dark:border-stone-800 pb-8">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
              <span className="text-[12px] font-mono font-bold text-stone-500 dark:text-stone-400 tracking-[0.3em] uppercase">Control_Center / Overview</span>
            </div>
            <motion.h1
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-3xl font-bold tracking-tight text-stone-900 dark:text-white uppercase"
            >
              Operations Dashboard
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="text-stone-500 mt-2 text-sm font-light uppercase tracking-widest leading-relaxed"
            >
              System ready. Welcome back, <span className="text-stone-600 dark:text-stone-300 font-mono text-[12px]">{user?.username || user?.name || user?.email || 'IDENTITY_UNKNOWN'}</span>. Monitoring active task payloads.
            </motion.p>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto"
          >
            <div className="relative group flex-1 sm:w-64">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Terminal className="h-3.5 w-3.5 text-stone-400 dark:text-stone-600 group-focus-within:text-emerald-500 transition-colors" />
              </div>
              <input
                type="text"
                aria-label="Search tasks"
                placeholder="SEARCH_REGISTRY..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2.5 bg-white dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] text-stone-900 dark:text-white text-xs font-mono focus:outline-none focus:border-emerald-600/60 w-full transition-all placeholder:text-stone-400 dark:placeholder:text-stone-500 shadow-sm"
              />
            </div>

            <div className="flex gap-2">
              <LuxuryButton
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className="px-6"
                aria-expanded={showFilters}
              >
                <FunnelIcon className="h-4 w-4 mr-2" />
                Parameters
              </LuxuryButton>

              <LuxuryButton
                onClick={() => setShowTaskForm(true)}
                className="px-6"
              >
                <PlusIcon className="h-4 w-4 mr-2" />
                Execute_Add
              </LuxuryButton>
            </div>
          </motion.div>
        </div>

        {/* Task Tab Terminal */}
        <div className="border-b border-stone-200 dark:border-stone-900 pb-px">
          <nav className="flex space-x-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "px-4 py-2 text-[11px] font-mono font-bold uppercase tracking-[0.2em] transition-all relative border-b-2",
                  activeTab === tab.id
                    ? 'text-emerald-600 dark:text-emerald-500 border-emerald-600 dark:border-emerald-500 bg-emerald-500/5'
                    : 'text-stone-400 dark:text-stone-600 border-transparent hover:text-stone-600 dark:hover:text-stone-400 hover:bg-stone-50 dark:hover:bg-stone-900/50'
                )}
              >
                {tab.name}
                <span className={cn(
                  "ml-2 px-1.5 py-0.5 rounded-[2px] text-[10px]",
                  activeTab === tab.id ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-stone-100 dark:bg-stone-900 text-stone-400 dark:text-stone-700'
                )}>
                  {tab.count.toString().padStart(2, '0')}
                </span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Statistics Cluster */}
      <AnimatePresence>
        {statistics && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <LuxuryStatisticsCard stats={statistics} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filters Interface */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mb-8"
          >
            <div className="space-y-4">
              <div className="flex items-center gap-3 px-2">
                <span className="text-[9px] font-mono text-stone-600 uppercase tracking-widest">Adjustment_Parameters</span>
                <div className="h-px flex-1 bg-stone-200 dark:bg-stone-800" />
              </div>
              <div className="bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] p-6">
                <TaskFilter />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Task Initialization Modal */}
      <AnimatePresence>
        {showTaskForm && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
              onClick={() => setShowTaskForm(false)}
            />
            <motion.div
              initial={{ scale: 0.98, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.98, opacity: 0, y: 10 }}
              className="relative w-full max-w-lg bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] shadow-[0_30px_100px_rgba(0,0,0,0.4)] overflow-hidden"
            >
              <div className="p-6 border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#141414] flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <PlusIcon className="h-4 w-4 text-emerald-600 dark:text-emerald-500" />
                  <h2 className="text-sm font-mono font-bold text-stone-900 dark:text-white uppercase tracking-widest">Operation_Initialization</h2>
                </div>
                <button
                  onClick={() => setShowTaskForm(false)}
                  aria-label="Close dialog"
                  className="p-2 -m-1 text-stone-500 hover:text-stone-900 dark:hover:text-white transition-colors"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="p-8">
                <LuxuryTaskForm
                  onSubmit={handleCreateTask}
                  onCancel={() => setShowTaskForm(false)}
                  isLoading={isCreatingTask}
                />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Primary Data Streams */}
      <div className="space-y-10">

        {/* Activity Stream */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-4"
        >
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-3 flex-1">
              <span className="text-[11px] font-mono text-stone-500 dark:text-stone-400 uppercase tracking-widest">Activity_Stream</span>
              <div className="h-px flex-1 bg-stone-200 dark:bg-stone-900" />
            </div>
          </div>

          <LuxuryCard variant="default">
            <LuxuryCardContent>
              {recentActivities.length > 0 ? (
                <div className="flow-root">
                  <ul role="list" className="-mb-8">
                    {recentActivities.map((activity, activityIdx) => (
                      <li key={activity.id}>
                        <div className="relative pb-8">
                          {activityIdx !== recentActivities.length - 1 ? (
                            <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-stone-100 dark:bg-stone-900" aria-hidden="true" />
                          ) : null}
                          <div className="relative flex space-x-4">
                            <div className="pt-1">
                              <span className={cn(
                                "h-8 w-8 rounded-[2px] flex items-center justify-center border",
                                activity.type === 'created' ? 'bg-blue-500/10 border-blue-500/20 text-blue-600 dark:text-blue-500' : 
                                activity.type === 'completed' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-500' :
                                'bg-amber-500/10 border-amber-500/20 text-amber-600 dark:text-amber-500'
                              )}>
                                {activity.type === 'created' ? <PlusIcon className="h-4 w-4" /> : 
                                 activity.type === 'completed' ? <CheckCircleIcon className="h-4 w-4" /> : 
                                 <DocumentTextIcon className="h-4 w-4" />}
                              </span>
                            </div>
                            <div className="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5">
                              <div>
                                <p className="text-sm text-stone-500 dark:text-stone-400">
                                  <span className="font-mono font-bold text-stone-500 dark:text-stone-400 mr-2">[{activity.type.toUpperCase()}]</span>
                                  Target: <span className="font-bold text-stone-900 dark:text-white tracking-tight">{activity.taskTitle}</span>
                                </p>
                              </div>
                              <div className="whitespace-nowrap text-right text-[11px] font-mono text-stone-400 dark:text-stone-600 uppercase">
                                <time dateTime={activity.timestamp}>{formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}</time>
                              </div>
                            </div>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="w-12 h-12 rounded-[4px] bg-stone-50 dark:bg-stone-900 flex items-center justify-center mx-auto mb-4 border border-stone-200 dark:border-stone-800 shadow-sm">
                    <Terminal className="h-5 w-5 text-stone-400 dark:text-stone-600" />
                  </div>
                  <h3 className="text-[11px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase tracking-[0.2em]">Stream_Empty</h3>
                  <p className="mt-1 text-[11px] text-stone-500 dark:text-stone-400 uppercase tracking-tighter">No recent telemetric signals detected.</p>
                </div>
              )}
            </LuxuryCardContent>
          </LuxuryCard>
        </motion.div>

        {/* Task Registry Feed */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 px-2">
            <div className="flex items-center gap-3 flex-1">
              <span className="text-[11px] font-mono text-stone-500 dark:text-stone-400 uppercase tracking-widest">Registry_Output</span>
              <div className="h-px flex-1 bg-stone-200 dark:bg-stone-900" />
            </div>
            
            <div className="flex items-center gap-2">
              <div className="flex bg-white dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] p-0.5 shadow-sm">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as 'created_at' | 'due_date' | 'priority')}
                  className="bg-transparent text-[11px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase px-3 py-1.5 focus:outline-none focus:text-emerald-600 dark:focus:text-emerald-500 transition-colors cursor-pointer"
                >
                  <option value="created_at" className="bg-white dark:bg-[#0f0f0f]">SORT: NEWEST</option>
                  <option value="due_date" className="bg-white dark:bg-[#0f0f0f]">SORT: DEADLINE</option>
                  <option value="priority" className="bg-white dark:bg-[#0f0f0f]">SORT: CRITICAL</option>
                </select>
                <div className="w-px bg-stone-200 dark:bg-stone-800 my-1" />
                <select
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                  className="bg-transparent text-[11px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase px-3 py-1.5 focus:outline-none focus:text-emerald-600 dark:focus:text-emerald-500 transition-colors cursor-pointer"
                >
                  <option value="desc" className="bg-white dark:bg-[#0f0f0f]">ORDER: DESC</option>
                  <option value="asc" className="bg-white dark:bg-[#0f0f0f]">ORDER: ASC</option>
                </select>
              </div>
            </div>
          </div>

          <LuxuryTaskList
            tasks={filteredAndSortedTasks}
            isLoading={tasksLoading}
            onTaskAction={handleTaskAction}
            onAddTask={() => setShowTaskForm(true)}
          />
        </motion.div>
      </div>
      
      <CompactChatWidget 
        onTaskUpdate={() => {
          if (user) {
            fetchTasks(user.id);
            fetchStatistics(user.id);
          }
        }} 
      />
    </LuxuryDashboardLayout>
  );
}