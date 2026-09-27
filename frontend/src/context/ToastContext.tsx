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
    (message: string, type: ToastType = 'success', durationMs = 2800) => {
      const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const newToast: Toast = { id, message, type, isExiting: false };

      setToasts((prev) => [...prev, newToast]);

      // Auto dismiss after 2.8s (or custom duration)
      const timeoutId = window.setTimeout(() => {
        removeToast(id);
      }, durationMs);

      timeoutsRef.current.set(id, timeoutId);
    },
    [removeToast]
  );

  const toastHelpers = {
    success: (msg: string, dur = 2800) => showToast(msg, 'success', dur),
    error: (msg: string, dur = 3500) => showToast(msg, 'error', dur),
    info: (msg: string, dur = 2800) => showToast(msg, 'info', dur),
    warning: (msg: string, dur = 3200) => showToast(msg, 'warning', dur),
  };

  const getTypeStyles = (type: ToastType) => {
    switch (type) {
      case 'success':
        return {
          title: 'Success',
          border: 'border-emerald-200 dark:border-emerald-800/80',
          iconBox: 'bg-emerald-50 dark:bg-emerald-950/70 text-emerald-600 dark:text-emerald-400 ring-1 ring-inset ring-emerald-600/20',
          titleColor: 'text-emerald-600 dark:text-emerald-400',
          icon: <CheckCircle2 className="h-5 w-5" />,
        };
      case 'error':
        return {
          title: 'Error',
          border: 'border-rose-200 dark:border-rose-800/80',
          iconBox: 'bg-rose-50 dark:bg-rose-950/70 text-rose-600 dark:text-rose-400 ring-1 ring-inset ring-rose-600/20',
          titleColor: 'text-rose-600 dark:text-rose-400',
          icon: <AlertCircle className="h-5 w-5" />,
        };
      case 'warning':
        return {
          title: 'Attention',
          border: 'border-amber-200 dark:border-amber-800/80',
          iconBox: 'bg-amber-50 dark:bg-amber-950/70 text-amber-600 dark:text-amber-400 ring-1 ring-inset ring-amber-600/20',
          titleColor: 'text-amber-600 dark:text-amber-400',
          icon: <AlertTriangle className="h-5 w-5" />,
        };
      default:
        return {
          title: 'Notice',
          border: 'border-indigo-200 dark:border-indigo-800/80',
          iconBox: 'bg-indigo-50 dark:bg-indigo-950/70 text-indigo-600 dark:text-indigo-400 ring-1 ring-inset ring-indigo-600/20',
          titleColor: 'text-indigo-600 dark:text-indigo-400',
          icon: <Info className="h-5 w-5" />,
        };
    }
  };

  return (
    <ToastContext.Provider value={{ showToast, toast: toastHelpers }}>
      {children}

      {/* Floating Top-Right SaaS Toast Container */}
      <div
        className="fixed top-6 right-6 z-50 flex flex-col gap-3 w-full max-w-[390px] pointer-events-none"
        aria-live="polite"
      >
        {toasts.map((item) => {
          const cfg = getTypeStyles(item.type);
          return (
            <div
              key={item.id}
              className={`pointer-events-auto flex items-start gap-3.5 p-4 rounded-2xl bg-white dark:bg-[#111726] shadow-[0_12px_36px_-6px_rgba(0,0,0,0.12),0_4px_14px_-2px_rgba(0,0,0,0.06)] border ${cfg.border} transform transition-all duration-300 ease-out ${
                item.isExiting
                  ? 'opacity-0 -translate-y-3 scale-95'
                  : 'opacity-100 translate-y-0 scale-100'
              }`}
            >
              {/* Left Soft Tint Icon Container */}
              <div className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 shadow-xs ${cfg.iconBox}`}>
                {cfg.icon}
              </div>

              {/* Message Content */}
              <div className="flex-1 min-w-0 pt-0.5">
                <span className={`block text-[11.5px] font-bold uppercase tracking-wider mb-0.5 ${cfg.titleColor}`}>
                  {cfg.title}
                </span>
                <p className="text-[13.5px] font-semibold text-slate-800 dark:text-slate-100 leading-snug break-words">
                  {item.message}
                </p>
              </div>

              {/* Close Button */}
              <button
                onClick={() => removeToast(item.id)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0 cursor-pointer -mr-1 -mt-1"
                title="Dismiss"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
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
