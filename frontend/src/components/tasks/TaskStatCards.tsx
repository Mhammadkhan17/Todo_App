'use client';

import { TaskStatistics } from '@/types';
import { motion } from 'framer-motion';
import { CheckCircleIcon, ClockIcon, ExclamationTriangleIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

import { cn } from '@/lib/utils';

interface TaskStatCardsProps {
  stats: TaskStatistics;
}

export function TaskStatCards({ stats }: TaskStatCardsProps) {
  const statCards = [
    {
      name: 'OPERATIONS_TOTAL',
      value: stats.total,
      icon: DocumentTextIcon,
      color: 'text-stone-400',
      borderColor: 'border-stone-800',
    },
    {
      name: 'SUCCESS_RATE',
      value: stats.completed,
      icon: CheckCircleIcon,
      color: 'text-emerald-500',
      borderColor: 'border-emerald-500/20',
    },
    {
      name: 'PENDING_TASKS',
      value: stats.pending,
      icon: ClockIcon,
      color: 'text-amber-500',
      borderColor: 'border-amber-500/20',
    },
    {
      name: 'OVERDUE_CRITICAL',
      value: stats.overdue,
      icon: ExclamationTriangleIcon,
      color: 'text-red-500',
      borderColor: 'border-red-500/20',
    },
  ];

  return (
    <div className="mb-8">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: index * 0.05 }}
            className={cn(
              "bg-white dark:bg-[#0f0f0f] border rounded-[4px] p-5 transition-all duration-200 hover:bg-stone-50 dark:hover:bg-[#141414] shadow-sm",
              stat.borderColor.includes('stone') ? 'border-stone-200 dark:border-stone-800' : stat.borderColor
            )}
          >
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-mono font-bold text-stone-400 dark:text-stone-500 tracking-widest">{stat.name}</p>
                <stat.icon className={cn("h-4 w-4", stat.color)} />
              </div>
              <p className="text-4xl font-bold font-mono tracking-tighter text-stone-900 dark:text-white tabular-nums">
                {stat.value.toString().padStart(2, '0')}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}