import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  width?: 'md' | 'lg' | 'xl' | '2xl';
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  children,
  width = 'xl',
}) => {
  const [mounted, setMounted] = useState(isOpen);
  const [visible, setVisible] = useState(false);
  const closingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (isOpen) {
      if (closingTimerRef.current) clearTimeout(closingTimerRef.current);
      setMounted(true);
      // Double rAF ensures the browser paints the offscreen state before sliding in
      const raf = requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setVisible(true);
        });
      });
      document.body.style.overflow = 'hidden';
      return () => cancelAnimationFrame(raf);
    } else {
      setVisible(false);
      closingTimerRef.current = setTimeout(() => {
        setMounted(false);
        document.body.style.overflow = '';
      }, 320);
      return () => {
        if (closingTimerRef.current) clearTimeout(closingTimerRef.current);
      };
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!mounted && !isOpen) return null;

  const widthStyles = {
    md: 'sm:max-w-md',
    lg: 'sm:max-w-lg',
    xl: 'sm:max-w-xl',
    '2xl': 'sm:max-w-2xl',
  };

  return createPortal(
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 overflow-hidden">
        {/* Backdrop with smooth fade transition */}
        <div
          className={`absolute inset-0 bg-slate-950/65 backdrop-blur-md transition-opacity duration-320 ease-out cursor-pointer ${
            visible ? 'opacity-100' : 'opacity-0'
          }`}
          onClick={onClose}
        />

        {/* Responsive Container: Bottom-aligned on mobile (modal view), right-aligned on desktop */}
        <div className="pointer-events-none fixed inset-0 sm:inset-y-0 sm:left-auto sm:right-0 flex flex-col justify-end sm:justify-start sm:max-w-full sm:pl-10 h-full">
          <div
            className={`pointer-events-auto w-full sm:w-screen ${widthStyles[width]} h-[92vh] sm:h-full rounded-t-3xl sm:rounded-none transform transition-transform duration-320 ease-[cubic-bezier(0.2,0.95,0.2,1)] will-change-transform bg-white dark:bg-[#111726] border-t sm:border-t-0 sm:border-l border-slate-200/90 dark:border-slate-800 shadow-[0_-16px_48px_rgba(0,0,0,0.25)] sm:shadow-[-16px_0_48px_rgba(0,0,0,0.18)] dark:sm:shadow-[-16px_0_48px_rgba(0,0,0,0.65)] flex flex-col ${
              visible
                ? 'translate-y-0 sm:translate-x-0'
                : 'translate-y-full sm:translate-y-0 sm:translate-x-full'
            }`}
          >
            {/* Mobile Drag Pill Handle */}
            <div className="sm:hidden pt-3 pb-1 flex justify-center shrink-0">
              <div className="w-12 h-1.5 rounded-full bg-slate-300 dark:bg-slate-700" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-200/90 dark:border-slate-800 px-5 sm:px-6 py-4 bg-white dark:bg-[#111726] sticky top-0 z-10 shrink-0">
              <div className="flex-1 pr-4 min-w-0">{title}</div>
              <button
                onClick={onClose}
                className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors active-pop cursor-pointer shrink-0"
                title="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content with Butter Scroll & Overscroll Contain */}
            <div className="flex-1 overflow-y-auto px-5 sm:px-6 py-5 sm:py-6 butter-scroll overscroll-contain scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700">
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};
