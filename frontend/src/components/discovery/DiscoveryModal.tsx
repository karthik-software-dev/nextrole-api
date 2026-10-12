import React, { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Pause,
  Play,
  Square,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  Database,
  Globe,
  Radio,
  Clock,
  Cpu,
} from 'lucide-react';
import { useDiscovery } from '../../context/DiscoveryContext';

export const DiscoveryModal: React.FC = () => {
  const {
    isDiscovering,
    isPaused,
    discoveryStatusText,
    pauseDiscovery,
    resumeDiscovery,
    stopDiscovery,
    isModalOpen,
    setIsModalOpen,
    useCache,
    lastSyncedCount,
  } = useDiscovery();

  const navigate = useNavigate();

  // Live elapsed timing counter
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!isDiscovering) {
      setElapsedSeconds(0);
      return;
    }
    if (isPaused) return;

    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [isDiscovering, isPaused]);

  // Determine current pipeline stage (1 to 4) based on status text
  const currentStep = useMemo(() => {
    const text = (discoveryStatusText || '').toLowerCase();
    if (text.includes('database') || text.includes('postgresql') || text.includes('syncing jobs')) {
      return 4;
    }
    if (text.includes('dedup') || text.includes('relevance') || text.includes('scoring') || text.includes('tier')) {
      return 3;
    }
    if (text.includes('normalizing') || text.includes('parse') || text.includes('schema')) {
      return 2;
    }
    return 1;
  }, [discoveryStatusText]);

  // Dynamic progress percentage for smooth animated loader bar
  const progressPercent = useMemo(() => {
    switch (currentStep) {
      case 1:
        return Math.min(28, 10 + elapsedSeconds * 2.5);
      case 2:
        return Math.min(52, 30 + elapsedSeconds * 1.8);
      case 3:
        return Math.min(78, 55 + elapsedSeconds * 1.2);
      case 4:
        return Math.min(96, 80 + elapsedSeconds * 0.8);
      default:
        return 15;
    }
  }, [currentStep, elapsedSeconds]);

  // Dismiss modal on Escape key press
  useEffect(() => {
    if (!isModalOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsModalOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModalOpen, setIsModalOpen]);

  if (!isModalOpen) return null;

  const handleClose = () => {
    setIsModalOpen(false);
  };

  const handleViewJobs = () => {
    setIsModalOpen(false);
    navigate('/jobs');
  };

  const steps = [
    { num: 1, label: '31 Engines', sub: 'Crawling' },
    { num: 2, label: 'Schema', sub: 'Parsing' },
    { num: 3, label: 'Relevance', sub: 'Scoring' },
    { num: 4, label: 'Postgres', sub: 'Upserting' },
  ];

  return (
    <div
      onClick={handleClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/75 backdrop-blur-xl animate-in fade-in duration-300 cursor-pointer"
    >
      {/* Background Animated Gradient Aura */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[520px] h-[520px] rounded-full bg-gradient-to-tr from-indigo-500/20 via-purple-500/15 to-cyan-500/20 blur-3xl animate-pulse [animation-duration:4s]" />
      </div>

      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-lg rounded-3xl bg-white/95 dark:bg-[#0e1322]/95 border border-slate-200/90 dark:border-slate-800/90 shadow-[0_25px_80px_-15px_rgba(0,0,0,0.5),0_0_50px_rgba(99,102,241,0.12)] overflow-hidden animate-in zoom-in-95 duration-200 cursor-default"
        role="dialog"
        aria-modal="true"
      >
        {/* Top Header Bar */}
        <div className="flex items-center justify-between px-6 pt-5 pb-3.5 border-b border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-900/30">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-xs shadow-indigo-500/30">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <span className="text-[14px] font-bold text-slate-900 dark:text-white leading-none block">
                NextRole Engine
              </span>
              <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                {isDiscovering ? (isPaused ? 'Pipeline paused' : 'Active crawler telemetry') : 'Sync cycle completed'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Mode Indicator Badge */}
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold tracking-wide uppercase ${
                useCache
                  ? 'bg-amber-100/90 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-300/80 dark:border-amber-800/60'
                  : 'bg-emerald-100/90 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300/80 dark:border-emerald-800/60'
              }`}
            >
              {useCache ? <Database className="h-3 w-3" /> : <Globe className="h-3 w-3" />}
              <span>{useCache ? 'Snapshot Cache' : 'Live Crawl'}</span>
            </span>

            {/* Minimize / Close */}
            <button
              onClick={handleClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              title="Close to background"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="px-6 sm:px-8 py-7 flex flex-col items-center text-center">
          {/* ============================================================== */}
          {/* SAAS PIPELINE HUB WITH FLOWING INGESTION BEAMS                 */}
          {/* ============================================================== */}
          <div className="relative mb-6 flex items-center justify-center w-56 h-56 sm:w-60 sm:h-60 select-none">
            {isDiscovering ? (
              <>
                {/* Outermost Expanding Echo Ripple */}
                {!isPaused && (
                  <div className="absolute inset-4 rounded-full border border-indigo-400/20 animate-[ping_3.5s_cubic-bezier(0,0,0.2,1)_infinite] pointer-events-none" />
                )}

                {/* Ambient Center Glow Disk */}
                <div className="absolute inset-12 rounded-full bg-gradient-to-tr from-indigo-500/15 via-purple-500/20 to-cyan-500/15 dark:from-indigo-900/35 dark:via-purple-900/35 dark:to-cyan-900/35 blur-xl pointer-events-none" />

                {/* SVG Circuit Tracks & Flowing Ingestion Laser Beams */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible" viewBox="0 0 240 240">
                  {/* Concentric Decorative Radar Tracks */}
                  <circle cx="120" cy="120" r="92" fill="none" stroke="currentColor" strokeWidth="1" className="text-slate-200/50 dark:text-slate-800/60" strokeDasharray="3 4" />
                  <circle cx="120" cy="120" r="64" fill="none" stroke="currentColor" strokeWidth="1" className="text-slate-200/60 dark:text-slate-800/80" />

                  {/* Static Conduit Traces */}
                  <line x1="120" y1="46" x2="120" y2="84" stroke="currentColor" strokeWidth="2" className="text-slate-200 dark:text-slate-800" strokeLinecap="round" />
                  <line x1="120" y1="194" x2="120" y2="156" stroke="currentColor" strokeWidth="2" className="text-slate-200 dark:text-slate-800" strokeLinecap="round" />
                  <line x1="46" y1="120" x2="84" y2="120" stroke="currentColor" strokeWidth="2" className="text-slate-200 dark:text-slate-800" strokeLinecap="round" />
                  <line x1="194" y1="120" x2="156" y2="120" stroke="currentColor" strokeWidth="2" className="text-slate-200 dark:text-slate-800" strokeLinecap="round" />

                  {/* Flowing Laser Data Beams (Moving Inward into Hub) */}
                  {!isPaused && (
                    <>
                      {/* Top: Indeed -> Core (Blue) */}
                      <line
                        x1="120"
                        y1="46"
                        x2="120"
                        y2="84"
                        stroke="#3b82f6"
                        strokeWidth="2.5"
                        strokeDasharray="8 16"
                        className="animate-flow-inward"
                        strokeLinecap="round"
                        style={{ filter: 'drop-shadow(0 0 4px #3b82f6)' }}
                      />
                      {/* Bottom: LinkedIn -> Core (Sky) */}
                      <line
                        x1="120"
                        y1="194"
                        x2="120"
                        y2="156"
                        stroke="#0ea5e9"
                        strokeWidth="2.5"
                        strokeDasharray="8 16"
                        className="animate-flow-inward"
                        strokeLinecap="round"
                        style={{ filter: 'drop-shadow(0 0 4px #0ea5e9)' }}
                      />
                      {/* Left: Naukri -> Core (Indigo) */}
                      <line
                        x1="46"
                        y1="120"
                        x2="84"
                        y2="120"
                        stroke="#818cf8"
                        strokeWidth="2.5"
                        strokeDasharray="8 16"
                        className="animate-flow-inward"
                        strokeLinecap="round"
                        style={{ filter: 'drop-shadow(0 0 4px #818cf8)' }}
                      />
                      {/* Right: ATS 30+ -> Core (Emerald) */}
                      <line
                        x1="194"
                        y1="120"
                        x2="156"
                        y2="120"
                        stroke="#10b981"
                        strokeWidth="2.5"
                        strokeDasharray="8 16"
                        className="animate-flow-inward"
                        strokeLinecap="round"
                        style={{ filter: 'drop-shadow(0 0 4px #10b981)' }}
                      />
                    </>
                  )}
                </svg>

                {/* Top Node: Indeed */}
                <div className="absolute top-1 left-1/2 -translate-x-1/2 flex flex-col items-center gap-0.5 z-20 group">
                  <div
                    className="flex items-center justify-center w-8 h-8 rounded-xl bg-[#003A9B] text-white shadow-md shadow-blue-800/30 border border-white/25 transition-transform group-hover:scale-105 cursor-pointer"
                    title="Indeed Crawl Engine"
                  >
                    <svg className="w-4 h-4 fill-white" viewBox="0 0 24 24">
                      <path d="M11.56 2.5C7.38 2.5 4 5.88 4 10.06c0 2.85 1.6 5.34 4.01 6.58l-.71 3.66 4.01-1.96c.09 0 .18.09.27.09 4.18 0 7.56-3.38 7.56-7.56 0-4.18-3.38-7.56-7.56zm-1.6 3.74c.71 0 1.25.54 1.25 1.25s-.54 1.25-1.25 1.25-1.25-.54-1.25-1.25.54-1.25 1.25-1.25zm-.18 3.56h1.69v5.79H9.78V9.8zm4.89 5.79h-1.69v-3.3c0-.71-.27-1.25-.98-1.25-.54 0-.89.36-1.07.8v3.75H9.24V9.8h1.69v.89c.45-.62 1.16-.98 1.96-.98 1.42 0 2.49.98 2.49 2.67v3.42z" />
                    </svg>
                  </div>
                  <span className="text-[9.5px] font-bold text-slate-600 dark:text-slate-300">Indeed</span>
                </div>

                {/* Bottom Node: LinkedIn */}
                <div className="absolute bottom-1 left-1/2 -translate-x-1/2 flex flex-col-reverse items-center gap-0.5 z-20 group">
                  <div
                    className="flex items-center justify-center w-8 h-8 rounded-xl bg-[#0A66C2] text-white shadow-md shadow-sky-600/30 border border-white/25 transition-transform group-hover:scale-105 cursor-pointer"
                    title="LinkedIn Live Ingestion"
                  >
                    <svg className="w-4 h-4 fill-white" viewBox="0 0 24 24">
                      <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.64 1.64 0 1 0-.01-3.28 1.64 1.64 0 0 0 .01 3.28m-1.4 9.74h2.81v-8.37H5.06v8.37Z" />
                    </svg>
                  </div>
                  <span className="text-[9.5px] font-bold text-slate-600 dark:text-slate-300">LinkedIn</span>
                </div>

                {/* Left Node: Naukri */}
                <div className="absolute left-1 top-1/2 -translate-y-1/2 flex items-center gap-1 z-20 group">
                  <div
                    className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-tr from-[#1b439b] to-[#1271D8] text-white shadow-md shadow-indigo-600/30 border border-white/25 transition-transform group-hover:scale-105 cursor-pointer"
                    title="Naukri Regional Stream"
                  >
                    <span className="font-black text-[13px] tracking-tight font-sans text-white">N</span>
                  </div>
                  <span className="text-[9.5px] font-bold text-slate-600 dark:text-slate-300">Naukri</span>
                </div>

                {/* Right Node: ATS 30+ */}
                <div className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-1 z-20 group">
                  <span className="text-[9.5px] font-bold text-slate-600 dark:text-slate-300">ATS 30+</span>
                  <div
                    className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-600 text-white shadow-md shadow-emerald-500/30 border border-white/25 transition-transform group-hover:scale-105 cursor-pointer"
                    title="Enterprise Direct ATS (Greenhouse, Lever, Workday 30+)"
                  >
                    <Cpu className="w-4 h-4 text-white" />
                  </div>
                </div>

                {/* Central Engine Hub Core */}
                <div className="relative z-10 flex h-16 w-16 sm:h-18 sm:w-18 items-center justify-center rounded-2xl sm:rounded-3xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 text-white shadow-[0_0_35px_rgba(99,102,241,0.5)] border border-indigo-300/30">
                  <Radio className={`h-8 w-8 text-white ${isPaused ? 'opacity-50' : 'animate-pulse'}`} />
                </div>
              </>
            ) : (
              <div className="relative flex items-center justify-center">
                <div className="absolute -inset-4 rounded-full bg-emerald-500/20 blur-xl animate-pulse" />
                <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-tr from-emerald-500 to-teal-500 text-white shadow-xl shadow-emerald-500/35 border border-emerald-300/30">
                  <CheckCircle2 className="h-11 w-11" />
                </div>
              </div>
            )}
          </div>

          {/* Dynamic Status Title */}
          <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            {isDiscovering
              ? isPaused
                ? 'Discovery Paused'
                : 'Ingesting Job Feeds...'
              : 'Discovery Complete!'}
          </h3>

          {/* Subtitle (Shown on complete or paused) */}
          {!isDiscovering && (
            <p className="mt-1.5 text-xs sm:text-[13px] text-slate-500 dark:text-slate-400 max-w-sm leading-relaxed">
              Successfully synced {lastSyncedCount} fresh verified opportunities into your database.
            </p>
          )}
          {isDiscovering && isPaused && (
            <p className="mt-1.5 text-xs text-amber-600 dark:text-amber-400 font-medium">
              Syncing is currently paused. Click Resume to continue.
            </p>
          )}

          {/* ============================================================== */}
          {/* PREMIUM ANIMATED GRADIENT LOADER BAR WITH LIVE TIMER           */}
          {/* ============================================================== */}
          {isDiscovering && (
            <div className="mt-5 w-full max-w-sm">
              {/* Header: Stage info + Live Timing Counter */}
              <div className="flex items-center justify-between text-xs mb-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse shrink-0" />
                  <span className="font-bold text-slate-800 dark:text-slate-200 text-[12px] truncate">
                    Stage {currentStep} of 4: {steps[currentStep - 1]?.label}
                  </span>
                </div>
                <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-mono font-bold text-[11px] border border-indigo-200/60 dark:border-indigo-800/60 shrink-0">
                  <Clock className="h-3 w-3" />
                  <span>{elapsedSeconds}s</span>
                </div>
              </div>

              {/* Glowing Gradient Animated Progress Bar with Shimmer & Leading Pulse */}
              <div className="relative h-[18px] w-full rounded-full bg-slate-100 dark:bg-slate-800/90 p-0.5 overflow-hidden border border-slate-200/90 dark:border-slate-700/70 shadow-inner">
                <div
                  className={`h-full rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 shadow-md shadow-indigo-500/30 transition-all duration-700 ease-out relative overflow-hidden animate-gradient-flow ${
                    isPaused ? '' : ''
                  }`}
                  style={{ width: `${progressPercent}%` }}
                >
                  {/* Moving Shimmer Sheen Wave across progress */}
                  {!isPaused && (
                    <div
                      className="absolute inset-0 w-full h-full animate-shimmer pointer-events-none"
                      style={{
                        background:
                          'linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.45) 50%, transparent 100%)',
                      }}
                    />
                  )}
                </div>
              </div>

              {/* 4 Step Milestones Beneath the Bar */}
              <div className="mt-3 grid grid-cols-4 gap-1.5 text-center">
                {steps.map((st) => {
                  const isPast = currentStep > st.num;
                  const isCurrent = currentStep === st.num;

                  return (
                    <div
                      key={st.num}
                      className={`flex flex-col items-center py-1 px-1 rounded-lg border transition-all ${
                        isCurrent
                          ? 'bg-indigo-50/80 dark:bg-indigo-950/60 border-indigo-200 dark:border-indigo-800/80 shadow-2xs'
                          : isPast
                          ? 'bg-emerald-50/60 dark:bg-emerald-950/40 border-emerald-200/60 dark:border-emerald-800/60'
                          : 'bg-slate-50/50 dark:bg-slate-900/40 border-slate-200/50 dark:border-slate-800/50 opacity-60'
                      }`}
                    >
                      <span
                        className={`text-[10px] font-bold truncate w-full transition-colors ${
                          isCurrent
                            ? 'text-indigo-700 dark:text-indigo-300'
                            : isPast
                            ? 'text-emerald-700 dark:text-emerald-300'
                            : 'text-slate-500 dark:text-slate-400'
                        }`}
                      >
                        {st.label}
                      </span>
                      <span
                        className={`text-[9px] font-semibold truncate w-full mt-0.5 ${
                          isCurrent
                            ? 'text-indigo-600 dark:text-indigo-400'
                            : isPast
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-slate-400 dark:text-slate-500'
                        }`}
                      >
                        {isPast ? '✓ Done' : isCurrent ? '● Active' : st.sub}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Action Button Controls */}
          <div className="mt-6 flex items-center gap-3 w-full justify-center">
            {isDiscovering ? (
              <>
                {/* Pause / Resume Button */}
                {isPaused ? (
                  <button
                    onClick={resumeDiscovery}
                    className="flex-1 max-w-[150px] inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white font-semibold text-xs shadow-md shadow-indigo-500/20 transition-all cursor-pointer"
                  >
                    <Play className="h-3.5 w-3.5 fill-white" />
                    <span>Resume</span>
                  </button>
                ) : (
                  <button
                    onClick={pauseDiscovery}
                    className="flex-1 max-w-[150px] inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-xs border border-slate-200 dark:border-slate-700 transition-all cursor-pointer"
                  >
                    <Pause className="h-3.5 w-3.5" />
                    <span>Pause</span>
                  </button>
                )}

                {/* Stop Button */}
                <button
                  onClick={stopDiscovery}
                  className="flex-1 max-w-[120px] inline-flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/60 dark:hover:bg-rose-900/60 text-rose-600 dark:text-rose-400 font-semibold text-xs border border-rose-200 dark:border-rose-900 transition-all cursor-pointer"
                  title="Stop syncing process"
                >
                  <Square className="h-3.5 w-3.5 fill-rose-600 dark:fill-rose-400" />
                  <span>Stop</span>
                </button>
              </>
            ) : (
              <button
                onClick={handleViewJobs}
                className="w-full max-w-xs inline-flex items-center justify-center gap-2 py-3 px-5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white font-bold text-xs shadow-lg shadow-indigo-500/25 transition-all cursor-pointer"
              >
                <span>Explore Discovered Jobs</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
