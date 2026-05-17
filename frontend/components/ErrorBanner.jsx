export default function ErrorBanner({ message, onClose }) {
  return (
    <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-start gap-3 animate-fade-in">
      <svg className="w-5 h-5 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" x2="12" y1="8" y2="12" />
        <line x1="12" x2="12.01" y1="16" y2="16" />
      </svg>
      <span className="flex-1">{message}</span>
      <button
        onClick={onClose}
        className="flex-shrink-0 p-1 rounded-lg hover:bg-red-100 transition text-red-400 hover:text-red-600"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 6 6 18" />
          <path d="m6 6 12 12" />
        </svg>
      </button>
    </div>
  );
}
