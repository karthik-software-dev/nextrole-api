import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  isExiting?: boolean;
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType, durationMs?: number) => void;
  toast: {
    success: (message: string, durationMs?: number) => void;
    error: (message: string, durationMs?: number) => void;
    info: (message: string, durationMs?: number) => void;
    warning: (message: string, durationMs?: number) => void;
  };
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timeoutsRef = useRef<Map<string, number>>(new Map());

  const removeToast = useCallback((id: string) => {
    // Start exit fade animation
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, isExiting: true } : t))
    );

    // Remove from state after animation finishes (250ms)
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
      const existingTimeout = timeoutsRef.current.get(id);
      if (existingTimeout) {
        window.clearTimeout(existingTimeout);
        timeoutsRef.current.delete(id);
      }
    }, 250);
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = 'success', durationMs = 1800) => {
      const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const newToast: Toast = { id, message, type, isExiting: false };

      setToasts((prev) => [...prev, newToast]);

      // Auto dismiss after 1-2 seconds (default 1800ms)
      const timeoutId = window.setTimeout(() => {
        removeToast(id);
      }, durationMs);

      timeoutsRef.current.set(id, timeoutId);
    },
    [removeToast]
  );

  const toastHelpers = {
    success: (msg: string, dur?: number) => showToast(msg, 'success', dur),
    error: (msg: string, dur?: number) => showToast(msg, 'error', dur),
    info: (msg: string, dur?: number) => showToast(msg, 'info', dur),
    warning: (msg: string, dur?: number) => showToast(msg, 'warning', dur),
  };

  const getIcon = (type: ToastType) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />;
      default:
        return <Info className="h-4 w-4 text-indigo-400 shrink-0" />;
    }
  };

  const getBorderColor = (type: ToastType) => {
    switch (type) {
      case 'success':
        return 'border-emerald-500/30';
      case 'error':
        return 'border-rose-500/30';
      case 'warning':
        return 'border-amber-500/30';
      default:
        return 'border-indigo-500/30';
    }
  };

  return (
    <ToastContext.Provider value={{ showToast, toast: toastHelpers }}>
      {children}

      {/* Floating Snackbar Container (Bottom-Right) */}
      <div
        className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-sm pointer-events-none"
        aria-live="polite"
      >
        {toasts.map((item) => (
          <div
            key={item.id}
            className={`pointer-events-auto flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-slate-900/95 dark:bg-[#111827]/95 backdrop-blur-md text-white text-xs font-medium shadow-2xl border ${getBorderColor(
              item.type
            )} transform transition-all duration-300 ease-out ${
              item.isExiting
                ? 'opacity-0 translate-y-2 scale-95'
                : 'opacity-100 translate-y-0 scale-100'
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              {getIcon(item.type)}
              <span className="truncate text-slate-100">{item.message}</span>
            </div>
            <button
              onClick={() => removeToast(item.id)}
              className="text-slate-400 hover:text-white p-0.5 rounded transition-colors shrink-0 cursor-pointer"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
