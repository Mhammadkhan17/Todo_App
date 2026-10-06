'use client';

import { TaskStatistics } from '@/types';
import { motion } from 'framer-motion';
import { CheckCircleIcon, ClockIcon, ExclamationTriangleIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface LuxuryStatisticsCardProps {
  stats: TaskStatistics;
}

export function LuxuryStatisticsCard({ stats }: LuxuryStatisticsCardProps) {
  const totalTasks = stats.total;
  const completionRate = totalTasks > 0 ? Math.round((stats.completed / totalTasks) * 100) : 0;

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
    <div className="mb-10">
      {/* Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
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

      {/* Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Completion Performance */}
        <motion.div
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] p-8 shadow-sm"
        >
          <div className="flex items-center gap-2 mb-8">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            <h3 className="text-[12px] font-mono font-bold text-stone-500 dark:text-stone-400 tracking-[0.2em] uppercase">Completion Performance</h3>
          </div>
          
          <div className="flex flex-col md:flex-row items-center justify-center gap-12">
            <div className="relative w-48 h-48">
              <svg className="w-48 h-48 transform -rotate-90" viewBox="0 0 120 120">
                <circle
                  cx="60"
                  cy="60"
                  r="56"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-stone-100 dark:text-[#1c1917]"
                />
                <circle
                  cx="60"
                  cy="60"
                  r="56"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="4"
                  strokeDasharray={`${completionRate * 3.51} 351`}
                  strokeLinecap="square"
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-stone-50/50 dark:bg-[#0a0a0a]/20 rounded-full">
                <div className="text-5xl font-bold font-mono text-stone-900 dark:text-white tabular-nums tracking-tighter">{completionRate}%</div>
                <div className="text-[11px] font-mono text-stone-400 dark:text-stone-500 tracking-widest uppercase mt-1">Efficiency</div>
              </div>
            </div>
            
            <div className="flex-1 space-y-6 w-full">
              <div className="space-y-2">
                <div className="flex justify-between text-[11px] font-mono text-stone-400 dark:text-stone-500 uppercase tracking-widest">
                  <span>Resource Distribution</span>
                  <span className="text-emerald-600 dark:text-emerald-500">{stats.completed}/{totalTasks}</span>
                </div>
                <div className="h-1.5 bg-stone-100 dark:bg-stone-900 rounded-full overflow-hidden">
                  <motion.div 
                    className="h-full bg-emerald-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${completionRate}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                  />
                </div>
              </div>
              <p className="text-sm text-stone-500 leading-relaxed font-light">
                Current operational efficiency is trending <span className="text-emerald-600 dark:text-emerald-400 font-mono text-[11px] uppercase">{completionRate > 70 ? 'Optimal' : 'Nominal'}</span>. 
                Task throughput is being monitored by the TodoFlow protocol.
              </p>
            </div>
          </div>
        </motion.div>

        {/* Priority Matrix */}
        <motion.div
          initial={{ opacity: 0, x: 4 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] p-8 shadow-sm"
        >
          <div className="flex items-center gap-2 mb-8">
            <div className="w-1.5 h-1.5 bg-amber-500 rounded-full" />
            <h3 className="text-[12px] font-mono font-bold text-stone-500 dark:text-stone-400 tracking-[0.2em] uppercase">Priority Priority Matrix</h3>
          </div>

          <div className="space-y-6">
            {[
              { label: 'Low Frequency', value: stats.priority_breakdown.low, color: 'bg-emerald-500', textColor: 'text-emerald-600 dark:text-emerald-500' },
              { label: 'Medium Priority', value: stats.priority_breakdown.medium, color: 'bg-amber-500', textColor: 'text-amber-600 dark:text-amber-500' },
              { label: 'High Criticality', value: stats.priority_breakdown.high, color: 'bg-red-500', textColor: 'text-red-600 dark:text-red-500' },
            ].map((item) => (
              <div key={item.label} className="space-y-3">
                <div className="flex justify-between items-end">
                  <div className="flex items-center gap-2">
                    <span className={cn("text-[11px] font-mono uppercase tracking-widest", item.textColor)}>{item.label}</span>
                  </div>
                  <span className="text-base font-mono font-bold text-stone-900 dark:text-white tabular-nums">{item.value.toString().padStart(2, '0')}</span>
                </div>
                <div className="h-1 bg-stone-100 dark:bg-stone-900 rounded-full overflow-hidden">
                  <motion.div
                    className={cn("h-full", item.color)}
                    initial={{ width: 0 }}
                    animate={{ width: `${totalTasks > 0 ? (item.value / totalTasks) * 100 : 0}%` }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-10 pt-6 border-t border-stone-100 dark:border-stone-900 flex justify-between items-center">
            <span className="text-[11px] font-mono text-stone-400 dark:text-stone-600 uppercase tracking-[0.2em]">Total Payload</span>
            <span className="text-sm font-mono font-bold text-stone-500 dark:text-stone-400 tabular-nums">0x{totalTasks.toString(16).toUpperCase()} UNIT</span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}