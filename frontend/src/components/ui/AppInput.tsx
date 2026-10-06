'use client';

import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  showPasswordToggle?: boolean;
  onTogglePassword?: () => void;
  passwordVisible?: boolean;
}

export function Input({
  label,
  error,
  showPasswordToggle = false,
  onTogglePassword,
  passwordVisible = false,
  className = '',
  ...props
}: InputProps) {
  const [isFocused, setIsFocused] = useState(false);

  const baseClasses = `
    block w-full rounded-[4px] border transition-all duration-200
    focus:outline-none focus:ring-0
    bg-[#141414] text-white
    placeholder-stone-600
    border-stone-800
    hover:border-stone-700
    focus:border-emerald-500/50
    text-sm px-4 py-2.5
  `;

  const focusClasses = isFocused
    ? 'border-emerald-500/50 bg-[#1a1a1a] shadow-[0_0_20px_rgba(16,185,129,0.05)]'
    : '';

  const errorClasses = error
    ? 'border-red-500/50 focus:border-red-500/80 bg-red-500/5'
    : '';

  const hoverClasses = 'hover:bg-[#1a1a1a]';

  const classes = `${baseClasses} ${focusClasses} ${errorClasses} ${hoverClasses} ${className}`;

  return (
    <div className="space-y-1.5">
      {label && (
        <label
          htmlFor={props.id}
          className="block text-[10px] font-mono font-medium text-stone-500 uppercase tracking-widest"
        >
          {label}
        </label>
      )}

      <div className="relative group">
        <input
          className={`${classes}${showPasswordToggle ? ' pr-11' : ''}`}
          onFocus={(e) => {
            setIsFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setIsFocused(false);
            props.onBlur?.(e);
          }}
          {...props}
        />

        {/* Password toggle button */}
        {showPasswordToggle && (
          <button
            type="button"
            onClick={onTogglePassword}
            className="absolute inset-y-0 right-3 flex items-center text-stone-600 hover:text-emerald-500 transition-colors"
            aria-label={passwordVisible ? "Hide password" : "Show password"}
          >
            {passwordVisible ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </button>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center space-x-2 text-red-400 mt-1" role="alert">
          <p className="text-xs font-mono uppercase tracking-tighter">{error}</p>
        </div>
      )}

      {/* Character count for password */}
      {props.type === 'password' && typeof props.value === 'string' && props.value.length > 0 && (
        <div className="flex justify-between items-center text-[9px] font-mono uppercase tracking-tighter text-stone-600">
          <span>LEN: {props.value.length}</span>
          <span
            className={props.value.length >= 8 ? 'text-emerald-500' : 'text-red-500'}
          >
            {props.value.length >= 8 ? 'SECURE' : 'WEAK'}
          </span>
        </div>
      )}
    </div>
  );
}