export default function Input({ label, error, className = '', leftIcon, ...props }) {
  return (
    <label className="block">
      <span className="text-sm font-semibold text-gray-700">{label}</span>
      {leftIcon ? (
        <div className="relative mt-1">
          <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-gray-400">
            {leftIcon}
          </div>
          <input {...props} className={`input-field !pl-10 ${error ? '!border-red-500' : ''} ${className}`} />
        </div>
      ) : (
        <input {...props} className={`input-field mt-1 ${error ? '!border-red-500' : ''} ${className}`} />
      )}
      {error && <span className="text-xs text-red-600 mt-0.5">{error}</span>}
    </label>
  );
}
