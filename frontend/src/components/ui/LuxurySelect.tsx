'use client';

import React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Option {
  value: string;
  label: string;
}

interface LuxurySelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  options: Option[];
}

export function LuxurySelect({
  label,
  error,
  helperText,
  options,
  className = '',
  ...props
}: LuxurySelectProps) {
  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label className="block text-[10px] font-mono font-bold text-stone-500 uppercase tracking-widest">
          {label}
        </label>
      )}

      <div className="relative">
        <select
          {...props}
          className={cn(
            "w-full px-4 py-2.5 bg-white dark:bg-[#141414] border rounded-[4px] text-stone-900 dark:text-white text-sm focus:outline-none focus:border-emerald-600/60 appearance-none transition-colors",
            error ? 'border-red-500/50' : 'border-stone-300 dark:border-stone-800',
            className
          )}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-stone-500 dark:text-stone-400">
          <ChevronDown className="h-4 w-4" />
        </div>
      </div>

      {error && (
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {!error && helperText && (
        <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">{helperText}</p>
      )}
    </div>
  );
}