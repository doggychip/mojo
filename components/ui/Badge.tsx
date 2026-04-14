'use client';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'lime' | 'green' | 'red' | 'cyan' | 'gray';
  size?: 'sm' | 'md';
}

const variantStyles: Record<string, string> = {
  lime: 'bg-[rgba(200,230,74,0.15)] text-[#C8E64A]',
  green: 'bg-[rgba(34,197,94,0.15)] text-[#22C55E]',
  red: 'bg-[rgba(239,68,68,0.15)] text-[#EF4444]',
  cyan: 'bg-[rgba(6,182,212,0.15)] text-[#06B6D4]',
  gray: 'bg-[rgba(255,255,255,0.08)] text-[#AAAAAA]',
};

export default function Badge({ children, variant = 'gray', size = 'sm' }: BadgeProps) {
  const sizeStyles = size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1';
  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold uppercase tracking-wide ${variantStyles[variant]} ${sizeStyles}`}
    >
      {children}
    </span>
  );
}
