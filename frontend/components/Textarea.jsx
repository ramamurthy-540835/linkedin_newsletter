export default function Textarea({ label, maxChars = 3000, value = '', rows = 4, ...props }) {
  const charCount = value.length;
  const countColor = charCount >= 3000
    ? 'text-red-500 font-semibold'
    : charCount >= 2700
      ? 'text-amber-500'
      : 'text-gray-400';

  return (
    <label className="block">
      <span className="text-sm font-semibold text-gray-700">{label}</span>
      <div className="relative mt-1">
        <textarea
          {...props}
          value={value}
          rows={rows}
          className="input-field resize-y"
        />
        <div className={`absolute bottom-2 right-3 text-xs ${countColor}`}>
          {charCount}/{maxChars}
        </div>
      </div>
    </label>
  );
}
