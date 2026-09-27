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
      }, 350);
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
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
  };

  return createPortal(
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 overflow-hidden">
        {/* Backdrop with smooth fade transition */}
        <div
          className={`absolute inset-0 bg-slate-950/65 backdrop-blur-md transition-opacity duration-300 ease-out cursor-pointer ${
            visible ? 'opacity-100' : 'opacity-0'
          }`}
          onClick={onClose}
        />

        <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10 h-full">
          <div
            className={`pointer-events-auto w-screen ${widthStyles[width]} h-full transform transition-transform duration-350 ease-[cubic-bezier(0.16,1,0.3,1)] bg-white dark:bg-[#111726] border-l border-slate-200/90 dark:border-slate-800 shadow-[-16px_0_48px_rgba(0,0,0,0.18)] dark:shadow-[-16px_0_48px_rgba(0,0,0,0.65)] flex flex-col ${
              visible ? 'translate-x-0' : 'translate-x-full'
            }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-200/90 dark:border-slate-800 px-6 py-4.5 bg-white dark:bg-[#111726] sticky top-0 z-10 shrink-0">
              <div className="flex-1 pr-4 min-w-0">{title}</div>
              <button
                onClick={onClose}
                className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer"
                title="Close drawer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-6 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700">
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};
