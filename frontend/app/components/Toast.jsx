'use client';

import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

const ToastContext = createContext(null);

const TYPE_STYLES = {
  success: 'border-green-200 bg-green-50 text-green-800',
  error: 'border-red-200 bg-red-50 text-red-800',
  info: 'border-blue-200 bg-blue-50 text-blue-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((message, type = 'info') => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => dismiss(id), 4000);
    return id;
  }, [dismiss]);

  const value = useMemo(() => ({ push, dismiss }), [push, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] space-y-2">
        {toasts.map((toast) => (
          <div key={toast.id} className={`w-80 border rounded-xl shadow-lg overflow-hidden animate-[toastIn_250ms_ease-out] ${TYPE_STYLES[toast.type] || TYPE_STYLES.info}`}>
            <div className="px-4 py-3 text-sm font-semibold">{toast.message}</div>
            <div className="h-1 bg-black/10"><div className="h-full bg-black/30 animate-[toastShrink_4s_linear_forwards]" /></div>
          </div>
        ))}
      </div>
      <style jsx global>{`@keyframes toastIn {from { transform: translateX(20px); opacity: 0; }to { transform: translateX(0); opacity: 1; }}@keyframes toastShrink {from { width: 100%; }to { width: 0%; }}`}</style>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
