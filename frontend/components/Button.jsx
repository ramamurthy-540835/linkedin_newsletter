import Link from 'next/link';

export default function Button({ href, onClick, children, variant = 'primary', size = 'md', className = '', disabled = false, loading = false }) {
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  const baseStyles = `${sizeStyles[size]} rounded-xl font-semibold transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2`;

  const variantStyles = {
    primary: 'bg-gradient-to-r from-studio-600 to-linkedin-600 text-white hover:from-studio-700 hover:to-linkedin-700 shadow-sm',
    secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200',
    danger: 'bg-red-600 text-white hover:bg-red-700',
    outline: 'border border-studio-200 text-studio-700 hover:bg-studio-50 bg-transparent',
    ghost: 'text-gray-600 hover:bg-gray-100 bg-transparent',
  };

  const styles = `${baseStyles} ${variantStyles[variant]} ${className}`;

  const spinner = (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );

  if (href) {
    return (
      <Link href={href} className={styles}>
        {children}
      </Link>
    );
  }

  return (
    <button onClick={onClick} disabled={disabled || loading} className={styles}>
      {loading && spinner}
      {children}
    </button>
  );
}
