export default function LoadingSpinner({ size = 'md', label }) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-10 h-10',
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <span className={`inline-block ${sizeClasses[size]} border-2 border-gray-200 border-t-studio-600 rounded-full animate-spin`} />
      {label && <span className="text-sm text-gray-500">{label}</span>}
    </div>
  );
}
