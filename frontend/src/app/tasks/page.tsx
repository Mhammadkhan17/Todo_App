'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState, useMemo } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useTasks } from '@/hooks/useTasks';
import { CreateTaskData, Task, TaskFilter } from '@/types';
import LuxuryDashboardLayout from '@/components/layout/LuxuryDashboardLayout';
import { LuxuryTaskList } from '@/components/tasks/LuxuryTaskList';
import { LuxuryTaskFilters } from '@/components/tasks/LuxuryTaskFilters';
import { LuxuryTaskForm } from '@/components/tasks/LuxuryTaskForm';
import { TaskStatCards } from '@/components/tasks/TaskStatCards';
import { LuxuryCard, LuxuryCardContent } from '@/components/ui/LuxuryCard';
import { LuxuryButton } from '@/components/ui/LuxuryButton';
import { PlusIcon } from '@heroicons/react/24/outline';
import CompactChatWidget from '@/components/chat/CompactChatWidget';
import { motion } from 'framer-motion';

export default function TasksPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth(); // Get auth loading state
  const { tasks, statistics, isLoading: tasksLoading, createTask, toggleTask, deleteTask, fetchTasks, fetchStatistics } = useTasks();
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const [filters, setFilters] = useState<TaskFilter>({});

  // Apply filters to tasks - must be called before any conditional returns (hooks must always run in same order)
  const filteredTasks = useMemo(() => {
    if (!Array.isArray(tasks)) {
      return [];
    }

    return tasks.filter(task => {
      // Apply priority filter
      if (filters.priority) {
        if (task.priority !== filters.priority) {
          return false;
        }
      }

      // Apply completed filter (including overdue)
      if (filters.completed !== undefined) {
        if (filters.completed === 'overdue') {
          // Overdue means the task has a due date in the past and is not completed
          if (!task.due_date || task.completed) {
            return false;
          }
          const dueDate = new Date(task.due_date);
          const currentDate = new Date();
          if (dueDate >= currentDate) {
            return false;
          }
        } else {
          // Regular completed filter (true/false)
          if (task.completed !== filters.completed) {
            return false;
          }
        }
      }

      // Apply due date range filter
      if (filters.due_date) {
        if (filters.due_date.start || filters.due_date.end) {
          if (task.due_date) {
            const taskDate = new Date(task.due_date);

            // Check start date
            if (filters.due_date.start) {
              const startDate = new Date(filters.due_date.start);
              if (taskDate < startDate) {
                return false;
              }
            }

            // Check end date
            if (filters.due_date.end) {
              const endDate = new Date(filters.due_date.end);
              // Set end date to end of day (23:59:59) for inclusive comparison
              endDate.setHours(23, 59, 59, 999);
              if (taskDate > endDate) {
                return false;
              }
            }
          } else {
            // If task has no due date but filter expects one, exclude it
            return false;
          }
        }
      }

      // Apply search filter
      if (filters.search && filters.search.trim() !== '') {
        const searchTerm = filters.search.toLowerCase().trim();
        const matchesTitle = task.title.toLowerCase().includes(searchTerm);
        const matchesDescription = task.description ?
          task.description.toLowerCase().includes(searchTerm) : false;

        if (!matchesTitle && !matchesDescription) {
          return false;
        }
      }

      // If all filters passed, include the task
      return true;
    });
  }, [tasks, filters]);

  // Redirect to login if not authenticated
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

  const handleCreateTask = async (data: CreateTaskData) => {
    setIsCreatingTask(true);
    try {
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

  const handleFilterChange = (newFilters: TaskFilter) => {
    setFilters(newFilters);
  };

  return (
    <LuxuryDashboardLayout
      user={user || null}
      onLogout={logout}
    >
      <div className="space-y-10">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-6 border-b border-stone-200 dark:border-stone-800 pb-8">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-1 h-1 bg-emerald-500 rounded-full" />
              <span className="text-[10px] font-mono font-bold text-stone-500 tracking-[0.3em] uppercase">Control_Center / Tasks</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-stone-900 dark:text-white uppercase">Task Registry</h1>
            <p className="text-stone-500 mt-2 text-xs font-light uppercase tracking-widest leading-relaxed">
              Active operation monitoring and task payload management protocol.
            </p>
          </div>

          <LuxuryButton
            onClick={() => setShowTaskForm(!showTaskForm)}
            className="w-full sm:w-auto"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            {showTaskForm ? 'Cancel_Action' : 'Initialize_Task'}
          </LuxuryButton>
        </div>

        {/* Statistics Cards */}
        {statistics && (
          <TaskStatCards stats={statistics} />
        )}

        {/* Filters */}
        <div className="space-y-4">
          <div className="flex items-center gap-3 px-2">
            <span className="text-[9px] font-mono text-stone-600 uppercase tracking-widest">Query_Parameters</span>
            <div className="h-px flex-1 bg-stone-200 dark:bg-stone-800" />
          </div>
          <LuxuryTaskFilters onFilterChange={handleFilterChange} />
        </div>

        {/* Task Form */}
        {showTaskForm && (
          <motion.div
            initial={{ opacity: 0, scale: 0.99 }}
            animate={{ opacity: 1, scale: 1 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-3 px-2">
              <span className="text-[9px] font-mono text-emerald-500 uppercase tracking-widest">New_Entry_Input</span>
              <div className="h-px flex-1 bg-emerald-500/20" />
            </div>
            <LuxuryCard variant="elevated">
              <LuxuryCardContent>
                <LuxuryTaskForm
                  onSubmit={handleCreateTask}
                  onCancel={() => setShowTaskForm(false)}
                  isLoading={isCreatingTask}
                />
              </LuxuryCardContent>
            </LuxuryCard>
          </motion.div>
        )}

        {/* Task List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-3 flex-1">
              <span className="text-[9px] font-mono text-stone-600 uppercase tracking-widest">Registry_Output</span>
              <div className="h-px flex-1 bg-stone-200 dark:bg-stone-800" />
            </div>
            <div className="ml-4 flex items-center gap-2">
              <span className="text-[10px] font-mono text-stone-500 tracking-tighter">COUNT:</span>
              <span className="text-[10px] font-mono font-bold text-emerald-500 bg-emerald-500/5 px-2 py-0.5 border border-emerald-500/20 rounded-[2px]">
                {filteredTasks.length.toString().padStart(3, '0')}
              </span>
            </div>
          </div>
          
          <LuxuryTaskList
            tasks={filteredTasks}
            isLoading={tasksLoading}
            onTaskAction={handleTaskAction}
            onAddTask={() => setShowTaskForm(true)}
          />
        </div>
      </div>
      <CompactChatWidget />
    </LuxuryDashboardLayout>
  );
}

// Add the missing imports and component functions that were referenced but not defined in the original code