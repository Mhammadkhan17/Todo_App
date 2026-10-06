import * as React from 'react';

interface LuxuryCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'elevated' | 'floating' | 'transparent';
  size?: 'sm' | 'md' | 'lg';
  border?: boolean;
}

const LuxuryCard = React.forwardRef<HTMLDivElement, LuxuryCardProps>(
  ({ children, className = '', variant = 'default', size = 'md', border = true, ...props }, ref) => {
    const baseClasses = 'rounded-[4px] transition-all duration-300';

    const variantClasses = {
      default: 'bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 shadow-sm dark:shadow-[0_4px_20px_rgba(0,0,0,0.3)]',
      elevated: 'bg-white dark:bg-[#141414] border border-stone-200 dark:border-stone-700 shadow-md dark:shadow-[0_10px_40px_rgba(0,0,0,0.4)]',
      floating: 'bg-white dark:bg-[#1a1a1a] border border-stone-300 dark:border-stone-600 shadow-lg dark:shadow-[0_20px_60px_rgba(0,0,0,0.5)]',
      transparent: 'bg-stone-50/40 dark:bg-[#0a0a0a]/40 backdrop-blur-md border border-stone-200 dark:border-stone-800/50 shadow-inner'
    };

    const sizeClasses = {
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8'
    };

    const borderClass = border ? '' : 'border-0';

    const classes = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${borderClass} ${className}`;

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);
LuxuryCard.displayName = 'LuxuryCard';

interface LuxuryCardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const LuxuryCardHeader = ({ children, className = '', ...props }: LuxuryCardHeaderProps) => (
  <div className={`mb-6 flex items-center justify-between border-b border-stone-100 dark:border-stone-800/50 pb-4 ${className}`} {...props}>
    {children}
  </div>
);

interface LuxuryCardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

const LuxuryCardTitle = ({ children, className = '', as: Tag = 'h3', ...props }: LuxuryCardTitleProps) => {
  const baseClasses = 'font-bold text-stone-900 dark:text-white tracking-tight text-sm uppercase tracking-widest font-mono text-stone-500 dark:text-stone-400';
  return (
    <Tag className={`${baseClasses} ${className}`} {...props}>
      {children}
    </Tag>
  );
};

interface LuxuryCardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

const LuxuryCardDescription = ({ children, className = '', ...props }: LuxuryCardDescriptionProps) => (
  <p className={`mt-2 text-sm text-stone-600 dark:text-stone-400 ${className}`} {...props}>
    {children}
  </p>
);

interface LuxuryCardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const LuxuryCardContent = ({ children, className = '', ...props }: LuxuryCardContentProps) => (
  <div className={`flex-1 ${className}`} {...props}>
    {children}
  </div>
);

interface LuxuryCardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const LuxuryCardFooter = ({ children, className = '', ...props }: LuxuryCardFooterProps) => (
  <div className={`mt-6 pt-6 border-t border-stone-200 dark:border-stone-700/50 ${className}`} {...props}>
    {children}
  </div>
);

export {
  LuxuryCard,
  LuxuryCardHeader,
  LuxuryCardTitle,
  LuxuryCardDescription,
  LuxuryCardContent,
  LuxuryCardFooter
};