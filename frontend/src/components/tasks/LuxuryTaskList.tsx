'use client';

import { Task } from '@/types';
import { LuxuryTaskItem } from './LuxuryTaskItem';
import { AnimatePresence } from 'framer-motion';
import { PlusIcon } from '@heroicons/react/24/outline';

interface LuxuryTaskListProps {
  tasks: Task[];
  isLoading?: boolean;
  onTaskAction?: (action: 'toggle' | 'edit' | 'delete', task: Task) => void;
  onAddTask?: () => void;
}

export function LuxuryTaskList({ tasks, isLoading, onTaskAction, onAddTask }: LuxuryTaskListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, index) => (
          <div
            key={index}
            className="bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] p-5 h-[100px] animate-pulse relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-stone-100 dark:via-stone-800/10 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" />
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="h-2 bg-stone-100 dark:bg-stone-800 rounded w-1/4 mb-4"></div>
                <div className="h-4 bg-stone-100 dark:bg-stone-800 rounded w-3/4 mb-3"></div>
                <div className="h-2 bg-stone-100 dark:bg-stone-800 rounded w-1/2"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="border border-dashed border-stone-300 dark:border-stone-800 rounded-[4px] py-20 bg-white/50 dark:bg-[#0a0a0a]/50">
        <div className="text-center max-w-xs mx-auto">
          <div className="inline-flex w-12 h-12 rounded-[4px] bg-stone-50 dark:bg-[#141414] border border-stone-200 dark:border-stone-800 items-center justify-center mb-6">
            <PlusIcon className="h-5 w-5 text-stone-400 dark:text-stone-600" />
          </div>
          <h3 className="text-xs font-mono font-bold text-stone-900 dark:text-white tracking-[0.2em] uppercase mb-2">Registry_Empty</h3>
          <p className="text-xs text-stone-500 font-light mb-8 uppercase tracking-tighter">
            No active operations detected in current context.
          </p>
          {onAddTask && (
            <button
              onClick={onAddTask}
              className="w-full min-h-11 py-3 bg-stone-100 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-[10px] font-mono font-bold text-stone-600 dark:text-stone-400 uppercase tracking-widest hover:bg-stone-200 dark:hover:bg-stone-800 hover:text-stone-900 dark:hover:text-white transition-all rounded-[4px] inline-flex items-center justify-center gap-2"
            >
              <PlusIcon className="h-4 w-4" />
              Initialize Task
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <AnimatePresence>
        {tasks.map((task) => (
          <LuxuryTaskItem
            key={task.id}
            task={task}
            onToggle={() => onTaskAction?.('toggle', task)}
            onEdit={() => onTaskAction?.('edit', task)}
            onDelete={() => onTaskAction?.('delete', task)}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}