'use client';

import { Task } from '@/types';
import { motion } from 'framer-motion';
import { CheckCircleIcon, ClockIcon, ExclamationTriangleIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface TaskItemProps {
  task: Task;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function LuxuryTaskItem({ task, onToggle, onEdit, onDelete }: TaskItemProps) {
  const getPriorityInfo = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high':
        return { color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-500/20' };
      case 'medium':
        return { color: 'text-amber-500', bg: 'bg-amber-500/10', border: 'border-amber-500/20' };
      case 'low':
        return { color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' };
      default:
        return { color: 'text-stone-500', bg: 'bg-stone-500/10', border: 'border-stone-500/20' };
    }
  };

  const pInfo = getPriorityInfo(task.priority || 'medium');

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className={cn(
        "bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] p-4 transition-all duration-200 group hover:bg-stone-50 dark:hover:bg-[#141414] hover:border-stone-300 dark:hover:border-stone-700 shadow-sm",
        task.completed ? 'opacity-60' : ''
      )}
    >
      <div className="flex items-start gap-4">
        {/* Priority Indicator */}
        <div
          className={cn("flex-shrink-0 w-1.5 h-10 rounded-full", pInfo.color.replace('text', 'bg'))}
          role="img"
          aria-label={`Priority: ${task.priority || 'medium'}`}
        />

        <div className="flex-1 min-w-0">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-1">
                <span className={cn("text-[11px] font-mono font-medium uppercase tracking-[0.1em] px-1.5 py-0.5 rounded-[2px] border", pInfo.bg, pInfo.color, pInfo.border)}>
                  {task.priority || 'NORMAL'}
                </span>
                <span className="text-[11px] font-mono text-stone-500 dark:text-stone-500 uppercase tracking-tighter">ID: {task.id.toString().padStart(4, '0')}</span>
              </div>
              <h3 className={cn(
                "text-base font-bold tracking-tight",
                task.completed ? 'text-stone-400 dark:text-stone-500 line-through' : 'text-stone-900 dark:text-white'
              )}>
                {task.title}
              </h3>
              {task.description && (
                <p className="text-sm text-stone-500 mt-1 line-clamp-2 font-light">
                  {task.description}
                </p>
              )}

              {task.due_date && (
                <div className="flex items-center gap-3 mt-3">
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-stone-400 dark:text-stone-500 uppercase tracking-widest">
                    <ClockIcon className="h-3.5 w-3.5" />
                    <time dateTime={task.due_date}>
                      {new Date(task.due_date).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </time>
                  </div>
                  {new Date(task.due_date) < new Date() && !task.completed && (
                    <span className="text-[11px] font-mono text-red-600 dark:text-red-500 uppercase tracking-tighter flex items-center gap-1">
                      <ExclamationTriangleIcon className="h-3.5 w-3.5" />
                      TERMINAL_OVERDUE
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Action Matrix */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={onToggle}
                aria-pressed={task.completed}
                aria-label={task.completed ? `Mark "${task.title}" as incomplete` : `Mark "${task.title}" as complete`}
                className="min-h-11 min-w-11 flex items-center justify-center rounded-[4px] transition-all duration-200"
              >
                <span
                  className={cn(
                    "w-5 h-5 rounded-[2px] border transition-all duration-200 flex items-center justify-center",
                    task.completed
                      ? "bg-emerald-500 border-emerald-500 text-white dark:text-[#0a0a0a]"
                      : "border-stone-300 dark:border-stone-700 hover:border-emerald-500/50 bg-stone-50 dark:bg-[#141414]"
                  )}
                >
                  {task.completed && <CheckCircleIcon className="h-3.5 w-3.5" />}
                </span>
              </button>

              <div className="h-4 w-px bg-stone-200 dark:bg-stone-800 mx-1" />

              <div className="flex opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100 transition-opacity">
                <button
                  onClick={onEdit}
                  aria-label={`Edit task "${task.title}"`}
                  className="min-h-11 min-w-11 flex items-center justify-center text-stone-500 hover:text-stone-900 dark:hover:text-white hover:bg-stone-100 dark:hover:bg-stone-800 rounded-[4px] transition-colors"
                >
                  <PencilIcon className="h-4 w-4" />
                </button>

                <button
                  onClick={onDelete}
                  aria-label={`Delete task "${task.title}"`}
                  className="min-h-11 min-w-11 flex items-center justify-center text-stone-500 hover:text-red-600 dark:hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-[4px] transition-colors"
                >
                  <TrashIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}