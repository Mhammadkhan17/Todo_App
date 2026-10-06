'use client';

import { useState } from 'react';
import { TaskFilter } from '@/types';
import { LuxuryInput } from '../ui/LuxuryInput';
import { LuxurySelect } from '../ui/LuxurySelect';
import { getPriorityOptions } from '@/lib/utils';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

interface LuxuryTaskFiltersProps {
  onFilterChange: (filters: TaskFilter) => void;
}

export function LuxuryTaskFilters({ onFilterChange }: LuxuryTaskFiltersProps) {
  const [filters, setFilters] = useState<TaskFilter>({
    priority: undefined,
    completed: undefined,
    due_date: {
      start: undefined,
      end: undefined,
    },
    search: '',
  });

  const priorityOptions = getPriorityOptions();
  const prioritySelectOptions = [{ value: '', label: 'All Priorities' }, ...priorityOptions];

  const handleFilterChange = (key: keyof TaskFilter, value: string | boolean | undefined) => {
    const newFilters = { ...filters, [key]: value } as TaskFilter;
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleDateRangeChange = (key: 'start' | 'end', value: string) => {
    const newDueDate = {
      ...filters.due_date,
      [key]: value,
    };
    const newFilters = { ...filters, due_date: newDueDate };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const clearFilters = () => {
    const clearedFilters: TaskFilter = {
      priority: undefined,
      completed: undefined,
      due_date: { start: undefined, end: undefined },
      search: '',
    };
    setFilters(clearedFilters);
    onFilterChange(clearedFilters);
  };

  return (
    <div className="bg-white dark:bg-[#0f0f0f] rounded-[4px] border border-stone-200 dark:border-stone-800 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-stone-100 dark:border-stone-800/50">
        <div className="flex items-center gap-3">
          <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
          <h3 className="text-[12px] font-mono font-bold text-stone-500 dark:text-stone-400 tracking-[0.2em] uppercase">Operations_Filter</h3>
        </div>
        <button
          onClick={clearFilters}
          className="text-[11px] font-mono font-bold text-stone-400 hover:text-stone-900 dark:text-stone-500 dark:hover:text-white uppercase tracking-widest transition-colors flex items-center gap-2"
        >
          <ArrowPathIcon className="h-3 w-3" />
          Reset_Query
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2">
          <LuxuryInput
            id="search"
            type="text"
            label="Filter_by_text"
            placeholder="Search payload..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>

        <div>
          <LuxurySelect
            id="priority"
            label="Criticality"
            value={filters.priority || ''}
            onChange={(e) => handleFilterChange('priority', e.target.value || undefined)}
            options={prioritySelectOptions.map((option) => ({
              value: option.value,
              label: option.label,
            }))}
          />
        </div>

        <div>
          <LuxurySelect
            id="completed"
            label="Execution_Status"
            value={filters.completed === undefined ? '' : filters.completed.toString()}
            onChange={(e) => {
              const value = e.target.value;
              if (value === '') {
                handleFilterChange('completed', undefined);
              } else if (value === 'overdue') {
                handleFilterChange('completed', 'overdue');
              } else {
                handleFilterChange('completed', value === 'true');
              }
            }}
            options={[
              { value: '', label: 'All Operations' },
              { value: 'false', label: 'Pending' },
              { value: 'true', label: 'Completed' },
              { value: 'overdue', label: 'Overdue' },
            ]}
          />
        </div>

        <div className="lg:col-span-2 md:col-span-2">
          <label className="block text-[11px] font-mono font-bold text-stone-400 dark:text-stone-500 uppercase tracking-widest mb-1.5">
            Temporal_Range
          </label>
          <div className="flex gap-2 items-center">
            <LuxuryInput
              id="due_date_start"
              type="date"
              value={filters.due_date?.start || ''}
              onChange={(e) => handleDateRangeChange('start', e.target.value)}
              className="flex-1"
            />
            <span className="text-[11px] font-mono text-stone-300 dark:text-stone-700">→</span>
            <LuxuryInput
              id="due_date_end"
              type="date"
              value={filters.due_date?.end || ''}
              onChange={(e) => handleDateRangeChange('end', e.target.value)}
              className="flex-1"
            />
          </div>
        </div>
      </div>
    </div>
  );
}