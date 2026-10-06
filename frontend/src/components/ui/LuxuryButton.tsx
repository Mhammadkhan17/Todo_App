import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-[4px] text-[11px] font-mono uppercase tracking-widest transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald-500 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
  {
    variants: {
      variant: {
        default: 'bg-emerald-600 text-white dark:text-[#0a0a0a] font-bold shadow-sm dark:shadow-[0_0_20px_rgba(16,185,129,0.15)] hover:bg-emerald-500 hover:shadow-md dark:hover:shadow-[0_0_25px_rgba(16,185,129,0.25)]',
        destructive: 'bg-red-600/10 text-red-600 dark:text-red-500 border border-red-500/20 hover:bg-red-600 hover:text-white',
        outline: 'border border-stone-200 dark:border-stone-800 bg-transparent hover:bg-stone-100 dark:hover:bg-stone-800 hover:text-stone-900 dark:hover:text-white text-stone-500 dark:text-stone-400',
        secondary: 'bg-stone-100 dark:bg-[#1a1a1a] text-stone-600 dark:text-stone-200 border border-stone-200 dark:border-stone-800 hover:bg-stone-200 dark:hover:bg-stone-800 hover:border-stone-300 dark:hover:border-stone-700',
        ghost: 'hover:bg-stone-100 dark:hover:bg-stone-800 hover:text-stone-900 dark:hover:text-white text-stone-500',
        link: 'text-emerald-600 dark:text-emerald-500 underline-offset-4 hover:underline uppercase',
        elevated: 'bg-white dark:bg-[#141414] border border-stone-200 dark:border-stone-700 shadow-md hover:shadow-lg text-stone-700 dark:text-stone-200',
        floating: 'bg-white/90 dark:bg-[#1a1a1a]/90 backdrop-blur-sm border border-stone-200 dark:border-stone-600 shadow-xl hover:bg-stone-50 dark:hover:bg-[#242424] text-stone-900 dark:text-white',
      },
      size: {
        default: 'h-10 px-5',
        sm: 'h-8 px-3 text-[10px]',
        lg: 'h-12 px-8 text-xs',
        icon: 'h-10 w-10 p-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const LuxuryButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={buttonVariants({ variant, size, className })}
        ref={ref}
        {...props}
      />
    );
  }
);
LuxuryButton.displayName = 'LuxuryButton';

export { LuxuryButton, buttonVariants };