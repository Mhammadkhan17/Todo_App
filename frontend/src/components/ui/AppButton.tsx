'use client';

import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: React.ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  className = '',
  children,
  disabled,
  ...props
}: ButtonProps) {
  const baseClasses = `
    inline-flex items-center justify-center font-medium rounded-[4px]
    focus:outline-none focus:ring-2 focus:ring-offset-2
    transition-all duration-300
    disabled:cursor-not-allowed disabled:opacity-50
  `;

  const variantClasses = {
    primary: `
      bg-emerald-600 text-white
      hover:bg-emerald-700
      focus:ring-emerald-500/50
      shadow-lg hover:shadow-xl
      border border-emerald-500/20
    `,
    secondary: `
      bg-stone-200 text-stone-900 dark:bg-stone-700 dark:text-stone-100
      hover:bg-stone-300 dark:hover:bg-stone-600
      focus:ring-stone-500/30
      border border-stone-300 dark:border-stone-600
      shadow-md hover:shadow-xl
    `,
    outline: `
      border-2 border-stone-300 text-stone-700 dark:border-stone-600 dark:text-stone-300
      bg-transparent hover:bg-stone-100 dark:hover:bg-stone-800
      focus:ring-stone-500/40
      shadow-md hover:shadow-xl
    `,
    ghost: `
      text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100
      bg-transparent hover:bg-stone-100 dark:hover:bg-stone-800
      border border-transparent
      focus:ring-stone-500/30
    `,
    danger: `
      bg-red-600 text-white
      hover:bg-red-700
      focus:ring-red-500/50
      shadow-lg hover:shadow-xl
      border border-red-500/20
    `,
  };

  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-sm font-medium',
    lg: 'px-8 py-4 text-base font-semibold',
  };

  const disabledClasses = disabled || loading
    ? 'opacity-50 cursor-not-allowed pointer-events-none'
    : '';

  const classes = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${disabledClasses} ${className}`;

  return (
    <button
      className={classes}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin -ml-1 mr-3 h-5 w-5"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      )}
      <span className="relative">{children}</span>
    </button>
  );
}