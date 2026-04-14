'use client';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

const variantStyles: Record<string, string> = {
  primary: 'bg-[#C8E64A] text-[#0A0A0A] hover:bg-[#d4ec60] font-bold',
  secondary: 'bg-transparent border border-[#333] text-[#F5F5F5] hover:bg-[#262626]',
  danger: 'bg-transparent border border-[#EF4444] text-[#EF4444] hover:bg-[rgba(239,68,68,0.1)]',
  ghost: 'bg-transparent text-[#AAAAAA] hover:text-[#F5F5F5] hover:bg-[#1E1E1E]',
};

const sizeStyles: Record<string, string> = {
  sm: 'text-xs px-3 py-1.5 rounded-lg',
  md: 'text-sm px-4 py-2 rounded-xl',
  lg: 'text-sm px-5 py-2.5 rounded-xl',
};

export default function Button({
  children,
  variant = 'secondary',
  size = 'md',
  loading = false,
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
      )}
      {children}
    </button>
  );
}
