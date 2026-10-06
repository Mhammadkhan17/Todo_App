'use client';

import { useState } from 'react';
import { TaskFilter as TaskFilterType } from '@/types';
import { Button } from '../ui/AppButton';
import { Input } from '../ui/AppInput';
import { Select } from '../ui/Select';
import { getPriorityOptions } from '@/lib/utils';

interface TaskFilterProps {
  onFilterChange?: (filters: TaskFilterType) => void;
}

export function TaskFilter({ onFilterChange }: TaskFilterProps) {
  const [filters, setFilters] = useState<TaskFilterType>({
    priority: undefined,
    completed: undefined,
    search: '',
  });

  const priorityOptions = getPriorityOptions();

  const handleInputChange = (field: keyof TaskFilterType, value: string | boolean | undefined) => {
    const newFilters = { ...filters, [field]: value } as TaskFilterType;
    setFilters(newFilters);
    if (onFilterChange) {
      onFilterChange(newFilters);
    }
  };

  const handleClearFilters = () => {
    const clearedFilters = {
      priority: undefined,
      completed: undefined,
      search: '',
    };
    setFilters(clearedFilters);
    if (onFilterChange) {
      onFilterChange(clearedFilters);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Filters</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Input
          id="search"
          type="text"
          label="Search Tasks"
          placeholder="Search by title or description..."
          value={filters.search}
          onChange={(e) => handleInputChange('search', e.target.value)}
        />

        <Select
          id="priority"
          label="Priority"
          value={filters.priority || ''}
          onChange={(e) => handleInputChange('priority', e.target.value || undefined)}
          options={[
            { value: '', label: 'All Priorities' },
            ...priorityOptions.map(option => ({
              value: option.value,
              label: option.label,
            })),
          ]}
        />

        <Select
          id="status"
          label="Status"
          value={filters.completed === undefined ? '' : filters.completed.toString()}
          onChange={(e) => {
            if (e.target.value === '') {
              handleInputChange('completed', undefined);
            } else {
              handleInputChange('completed', e.target.value === 'true');
            }
          }}
          options={[
            { value: '', label: 'All Statuses' },
            { value: 'false', label: 'Pending' },
            { value: 'true', label: 'Completed' },
          ]}
        />
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button
          variant="outline"
          onClick={handleClearFilters}
        >
          Clear Filters
        </Button>
        <Button
          onClick={() => onFilterChange && onFilterChange(filters)}
        >
          Apply Filters
        </Button>
      </div>
    </div>
  );
}