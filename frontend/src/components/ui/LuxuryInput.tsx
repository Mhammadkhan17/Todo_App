'use client';

import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LuxuryInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  showPasswordToggle?: boolean;
  onTogglePassword?: () => void;
}

export function LuxuryInput({
  label,
  error,
  helperText,
  showPasswordToggle = false,
  onTogglePassword,
  className = '',
  ...props
}: LuxuryInputProps) {
  const [isVisible, setIsVisible] = useState(false);

  const toggleVisibility = () => {
    setIsVisible(!isVisible);
    if (onTogglePassword) {
      onTogglePassword();
    }
  };

  const type = props.type === 'password' && showPasswordToggle
    ? isVisible
      ? 'text'
      : 'password'
    : props.type;

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label className="block text-[10px] font-mono font-bold text-stone-500 uppercase tracking-widest">
          {label}
        </label>
      )}

      <div className="relative">
        <input
          {...props}
          type={type}
          className={cn(
            "w-full px-4 py-2.5 bg-white dark:bg-[#141414] border rounded-[4px] text-stone-900 dark:text-white text-sm focus:outline-none focus:border-emerald-600/60 transition-colors",
            error ? 'border-red-500/50' : 'border-stone-300 dark:border-stone-800',
            showPasswordToggle ? 'pr-12' : 'pr-4',
            className
          )}
        />

        {showPasswordToggle && (
          <button
            type="button"
            onClick={toggleVisibility}
            aria-label={isVisible ? 'Hide password' : 'Show password'}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-stone-500 hover:text-stone-700 dark:text-stone-400 dark:hover:text-stone-200"
          >
            {isVisible ? (
              <EyeOff className="h-5 w-5" />
            ) : (
              <Eye className="h-5 w-5" />
            )}
          </button>
        )}
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