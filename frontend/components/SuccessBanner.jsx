export default function SuccessBanner({ message, onClose }) {
  return (
    <div className="p-4 bg-green-50 border border-green-200 text-green-700 rounded-xl flex items-start gap-3 animate-fade-in">
      <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <path d="m9 11 3 3L22 4" />
      </svg>
      <span className="flex-1">{message}</span>
      <button
        onClick={onClose}
        className="flex-shrink-0 p-1 rounded-lg hover:bg-green-100 transition text-green-400 hover:text-green-600"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 6 6 18" />
          <path d="m6 6 12 12" />
        </svg>
      </button>
    </div>
  );
}
