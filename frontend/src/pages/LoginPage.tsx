import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  Shield,
  ArrowRight,
  Sun,
  Moon,
  Sparkles,
  Search,
  Filter,
  BarChart3,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [email, setEmail] = useState('rahulkarthik056@gmail.com');
  const [password, setPassword] = useState('#Karthick979');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If already logged in, redirect to intended target or /dashboard
  React.useEffect(() => {
    if (isAuthenticated) {
      const redirectPath = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(redirectPath, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMessage('Please enter both your email and password.');
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login({ email: email.trim(), password });
      const redirectPath = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(redirectPath, { replace: true });
    } catch (err: any) {
      console.error('Login failed:', err);
      setErrorMessage(err.message || 'Invalid email or password. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const fillAdminCredentials = () => {
    setEmail('rahulkarthik056@gmail.com');
    setPassword('#Karthick979');
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen lg:h-screen lg:max-h-screen lg:overflow-hidden relative flex flex-col justify-between p-4 sm:p-6 lg:px-10 lg:py-6 xl:px-12 xl:py-7 bg-[#FAF9FF] dark:bg-[#070B14] text-slate-900 dark:text-slate-100 transition-colors duration-200 selection:bg-indigo-500 selection:text-white overflow-x-hidden">
      {/* Soft Ambient Radial Background Blooms */}
      <div className="absolute top-[-14%] left-[-8%] w-[580px] h-[580px] rounded-full bg-indigo-200/18 dark:bg-indigo-900/12 blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-14%] right-[-8%] w-[560px] h-[560px] rounded-full bg-purple-200/15 dark:bg-purple-900/12 blur-[140px] pointer-events-none" />

      {/* Very Subtle Large Lavender Radial Glow Behind Center Decorative Area */}
      <div className="hidden lg:block absolute top-[40%] left-[54%] -translate-x-1/2 -translate-y-1/2 w-[520px] h-[520px] rounded-full bg-indigo-200/20 dark:bg-indigo-900/12 blur-[120px] pointer-events-none" />

      {/* Top Header: Contained to 1340px Frame for Clean Proximity */}
      <header className="w-full max-w-[1340px] mx-auto flex items-center justify-between z-20 shrink-0 mb-2 lg:mb-1">
        <div className="inline-flex items-center gap-3 select-none">
          <img
            src="/nextrole-icon.png"
            alt="NextRole"
            className="h-9 w-9 object-contain rounded-xl shadow-xs"
          />
          <span className="text-[25px] font-extrabold tracking-tight leading-none inline-flex items-center">
            <span className="text-slate-900 dark:text-white">Next</span>
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 dark:from-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">
              Role
            </span>
          </span>
        </div>

        {/* Compact Sun/Moon Theme Switcher */}
        <button
          type="button"
          onClick={toggleTheme}
          className="flex items-center gap-1.5 p-1 px-2 rounded-full bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border border-slate-200/80 dark:border-slate-800 shadow-2xs hover:shadow-xs transition-all cursor-pointer select-none"
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          <div
            className={`p-1 rounded-full transition-colors ${
              theme !== 'dark' ? 'bg-indigo-50 text-indigo-600' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sun className="h-3.5 w-3.5" />
          </div>
          <div
            className={`p-1 rounded-full transition-colors ${
              theme === 'dark' ? 'bg-indigo-950/80 text-indigo-400' : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Moon className="h-3.5 w-3.5" />
          </div>
        </button>
      </header>

      {/* Main Content Area: Tightened 1340px Max-Width with Subtle Abstract Pattern */}
      <main className="w-full max-w-[1340px] mx-auto flex-1 flex flex-col lg:flex-row items-center justify-between gap-8 lg:gap-8 xl:gap-12 z-10 my-auto min-h-0 py-2 lg:py-0 relative">
        {/* ======================================================== */}
        {/* SUBTLE ABSTRACT BACKGROUND PATTERN (Polished & Refined)  */}
        {/* ======================================================== */}
        <div
          className="hidden lg:block absolute inset-0 pointer-events-none select-none z-0 overflow-hidden"
          aria-hidden="true"
        >
          {/* SVG Canvas for Sweeping Curved Lines, Dot Matrices & Gradient Nodes */}
          <svg className="w-full h-full" viewBox="0 0 1340 780" fill="none">
            <defs>
              {/* Subtle line gradients with low, calm opacity */}
              <linearGradient id="curve-gradient-1" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#818CF8" stopOpacity="0.04" />
                <stop offset="45%" stopColor="#6366F1" stopOpacity="0.24" />
                <stop offset="85%" stopColor="#A855F7" stopOpacity="0.20" />
                <stop offset="100%" stopColor="#C084FC" stopOpacity="0.04" />
              </linearGradient>

              <linearGradient id="curve-gradient-2" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#C084FC" stopOpacity="0.04" />
                <stop offset="50%" stopColor="#818CF8" stopOpacity="0.18" />
                <stop offset="100%" stopColor="#4F46E5" stopOpacity="0.04" />
              </linearGradient>

              {/* 3D-Shaded Nodes Radial Gradients */}
              <radialGradient id="node-gradient-1" cx="30%" cy="25%" r="70%">
                <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
                <stop offset="25%" stopColor="#C084FC" />
                <stop offset="65%" stopColor="#6366F1" />
                <stop offset="100%" stopColor="#3730A3" />
              </radialGradient>

              <radialGradient id="node-gradient-2" cx="30%" cy="25%" r="70%">
                <stop offset="0%" stopColor="#E0E7FF" stopOpacity="0.9" />
                <stop offset="30%" stopColor="#818CF8" />
                <stop offset="70%" stopColor="#4F46E5" />
                <stop offset="100%" stopColor="#312E81" />
              </radialGradient>
            </defs>

            {/* Upper-Middle 6x4 Dot Matrix Grid (Low Opacity, Positioned in Center Gap) */}
            <g opacity="0.22" fill="#818CF8" className="dark:opacity-18">
              <circle cx="580" cy="160" r="1.8" /><circle cx="598" cy="160" r="1.8" /><circle cx="616" cy="160" r="1.8" /><circle cx="634" cy="160" r="1.8" /><circle cx="652" cy="160" r="1.8" /><circle cx="670" cy="160" r="1.8" />
              <circle cx="580" cy="178" r="1.8" /><circle cx="598" cy="178" r="1.8" /><circle cx="616" cy="178" r="1.8" /><circle cx="634" cy="178" r="1.8" /><circle cx="652" cy="178" r="1.8" /><circle cx="670" cy="178" r="1.8" />
              <circle cx="580" cy="196" r="1.8" /><circle cx="598" cy="196" r="1.8" /><circle cx="616" cy="196" r="1.8" /><circle cx="634" cy="196" r="1.8" /><circle cx="652" cy="196" r="1.8" /><circle cx="670" cy="196" r="1.8" />
              <circle cx="580" cy="214" r="1.8" /><circle cx="598" cy="214" r="1.8" /><circle cx="616" cy="214" r="1.8" /><circle cx="634" cy="214" r="1.8" /><circle cx="652" cy="214" r="1.8" /><circle cx="670" cy="214" r="1.8" />
            </g>

            {/* Lower-Middle 6x4 Dot Matrix Grid (Low Opacity, Positioned in Center Gap) */}
            <g opacity="0.20" fill="#818CF8" className="dark:opacity-16">
              <circle cx="780" cy="540" r="1.8" /><circle cx="798" cy="540" r="1.8" /><circle cx="816" cy="540" r="1.8" /><circle cx="834" cy="540" r="1.8" /><circle cx="852" cy="540" r="1.8" /><circle cx="870" cy="540" r="1.8" />
              <circle cx="780" cy="558" r="1.8" /><circle cx="798" cy="558" r="1.8" /><circle cx="816" cy="558" r="1.8" /><circle cx="834" cy="558" r="1.8" /><circle cx="852" cy="558" r="1.8" /><circle cx="870" cy="558" r="1.8" />
              <circle cx="780" cy="576" r="1.8" /><circle cx="798" cy="576" r="1.8" /><circle cx="816" cy="576" r="1.8" /><circle cx="834" cy="576" r="1.8" /><circle cx="852" cy="576" r="1.8" /><circle cx="870" cy="576" r="1.8" />
              <circle cx="780" cy="594" r="1.8" /><circle cx="798" cy="594" r="1.8" /><circle cx="816" cy="594" r="1.8" /><circle cx="834" cy="594" r="1.8" /><circle cx="852" cy="594" r="1.8" /><circle cx="870" cy="594" r="1.8" />
            </g>

            {/* Primary Sweeping Curve (Shifted Center-Right, Clear of Description Text) */}
            <path
              d="M 620,780 C 640,520 740,360 940,240"
              stroke="url(#curve-gradient-1)"
              strokeWidth="1.2"
              fill="none"
            />

            {/* Secondary Loop Arc */}
            <path
              d="M 720,780 C 760,490 840,330 1020,200"
              stroke="url(#curve-gradient-2)"
              strokeWidth="1.1"
              fill="none"
              strokeDasharray="4 6"
              opacity="0.55"
            />

            {/* Soft Cross Connecting Arc */}
            <path
              d="M 580,440 C 690,380 790,460 890,490"
              stroke="url(#curve-gradient-1)"
              strokeWidth="1.0"
              fill="none"
              opacity="0.38"
            />

            {/* Subtle Purple/Indigo Gradient Nodes Along the Arcs */}
            {/* Node 1: Upper Right along main curve */}
            <circle
              cx="820"
              cy="285"
              r="7"
              fill="url(#node-gradient-1)"
              filter="drop-shadow(0 2px 4px rgba(99, 102, 241, 0.2))"
            />
            {/* Node 2: Center Middle */}
            <circle
              cx="675"
              cy="415"
              r="8.5"
              fill="url(#node-gradient-1)"
              filter="drop-shadow(0 2px 5px rgba(124, 58, 237, 0.2))"
            />
            {/* Node 3: Center-Left */}
            <circle
              cx="640"
              cy="565"
              r="6"
              fill="url(#node-gradient-2)"
            />
            {/* Node 4: Lower Center */}
            <circle
              cx="725"
              cy="620"
              r="7.5"
              fill="url(#node-gradient-1)"
            />
          </svg>
        </div>

        {/* ======================================================== */}
        {/* Left Section: ~58% Width (Brand Typography & Features) */}
        {/* ======================================================== */}
        <div className="w-full lg:w-[58%] flex flex-col justify-center min-h-0 order-2 lg:order-1 z-10 my-auto">
          {/* Eyebrow */}
          <div className="mb-2.5 sm:mb-3">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50/90 dark:bg-indigo-950/60 border border-indigo-100/90 dark:border-indigo-900/50 text-[11px] sm:text-[11.5px] font-bold tracking-[0.2em] uppercase text-indigo-600 dark:text-indigo-400">
              YOUR JOB SEARCH WORKSPACE
            </span>
          </div>

          {/* 3-Line Punchy Heading */}
          <h1 className="text-3xl sm:text-5xl lg:text-[52px] xl:text-[58px] font-extrabold text-slate-900 dark:text-white leading-[1.05] tracking-tight mb-3 sm:mb-3.5 max-w-[620px]">
            Find the right<br />
            <span className="bg-gradient-to-r from-[#4B46E5] via-[#6D3DF5] to-[#7C3AED] dark:from-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">
              opportunities
            </span><br />
            for your next step.
          </h1>

          {/* Subtitle Description */}
          <p className="text-base sm:text-[17px] xl:text-[17.5px] text-slate-600 dark:text-slate-400 font-medium leading-relaxed max-w-xl mb-5 sm:mb-6">
            Search, track and manage jobs from multiple sources &mdash; all in one place.
          </p>

          {/* Compact Feature Rows (Subtle, Minimal, No Heavy Cards) */}
          <div className="space-y-3 sm:space-y-3.5 max-w-lg">
            {/* Feature 1 */}
            <div className="flex items-start gap-3.5">
              <div className="h-9 w-9 rounded-xl bg-indigo-50/80 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-100/80 dark:border-indigo-900/40 flex items-center justify-center shrink-0 shadow-2xs mt-0.5">
                <Search className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 leading-tight">
                  Search across multiple sources
                </h3>
                <p className="text-xs sm:text-[13px] text-slate-500 dark:text-slate-400 leading-snug mt-0.5">
                  Get relevant jobs from top job boards.
                </p>
              </div>
            </div>

            {/* Feature 2 */}
            <div className="flex items-start gap-3.5">
              <div className="h-9 w-9 rounded-xl bg-indigo-50/80 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-100/80 dark:border-indigo-900/40 flex items-center justify-center shrink-0 shadow-2xs mt-0.5">
                <Filter className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 leading-tight">
                  Smart filtering
                </h3>
                <p className="text-xs sm:text-[13px] text-slate-500 dark:text-slate-400 leading-snug mt-0.5">
                  Find the opportunities that match you.
                </p>
              </div>
            </div>

            {/* Feature 3 */}
            <div className="flex items-start gap-3.5">
              <div className="h-9 w-9 rounded-xl bg-indigo-50/80 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-100/80 dark:border-indigo-900/40 flex items-center justify-center shrink-0 shadow-2xs mt-0.5">
                <BarChart3 className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 leading-tight">
                  Track your progress
                </h3>
                <p className="text-xs sm:text-[13px] text-slate-500 dark:text-slate-400 leading-snug mt-0.5">
                  Stay organized and never miss an opportunity.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ======================================================== */}
        {/* Right Section: ~42% Width (Elevated Login Card) */}
        {/* ======================================================== */}
        <div className="w-full lg:w-[42%] flex flex-col items-center lg:items-end justify-center shrink-0 order-1 lg:order-2 z-10 my-auto">
          <div className="w-full max-w-[430px] xl:max-w-[445px]">
            <div className="bg-white dark:bg-[#0B0F19] rounded-[24px] border border-slate-200/80 dark:border-slate-800 shadow-xl shadow-indigo-500/5 p-7 sm:p-8 xl:p-9 transition-all">
              {/* Logo inside card */}
              <div className="flex items-center gap-2.5 mb-4 select-none">
                <img
                  src="/nextrole-icon.png"
                  alt="NextRole"
                  className="h-8 w-8 object-contain rounded-xl"
                />
                <span className="text-2xl font-extrabold tracking-tight leading-none inline-flex items-center">
                  <span className="text-slate-900 dark:text-white">Next</span>
                  <span className="bg-gradient-to-r from-indigo-600 to-violet-600 dark:from-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">
                    Role
                  </span>
                </span>
              </div>

              <h2 className="text-2xl sm:text-[26px] font-bold tracking-tight text-slate-900 dark:text-white leading-tight">
                Welcome back
              </h2>
              <p className="text-xs sm:text-[13px] text-slate-500 dark:text-slate-400 font-medium mt-1 mb-5">
                Sign in to access your job search workspace.
              </p>

              {/* Error Alert */}
              {errorMessage && (
                <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 flex items-start gap-2.5 animate-in fade-in slide-in-from-top-1 duration-150">
                  <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                  <span className="text-xs font-semibold text-red-800 dark:text-red-300 leading-tight flex-1">
                    {errorMessage}
                  </span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-3.5">
                {/* EMAIL ADDRESS */}
                <div>
                  <label
                    htmlFor="email-input"
                    className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5"
                  >
                    EMAIL ADDRESS
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Mail className="h-4 w-4" />
                    </div>
                    <input
                      id="email-input"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="rahulkarthik056@gmail.com"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950/70 text-slate-900 dark:text-white placeholder-slate-400 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-600 dark:focus:border-indigo-500 transition-all"
                    />
                  </div>
                </div>

                {/* PASSWORD */}
                <div>
                  <label
                    htmlFor="password-input"
                    className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5"
                  >
                    PASSWORD
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                      <Lock className="h-4 w-4" />
                    </div>
                    <input
                      id="password-input"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950/70 text-slate-900 dark:text-white placeholder-slate-400 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-600 dark:focus:border-indigo-500 transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {/* Remember Me & Admin Autofill Row */}
                <div className="flex items-center justify-between pt-0.5">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-indigo-600 focus:ring-indigo-500/20 cursor-pointer"
                    />
                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                      Remember me for this session
                    </span>
                  </label>

                  <button
                    type="button"
                    onClick={fillAdminCredentials}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors cursor-pointer inline-flex items-center gap-1"
                    title="Autofill default admin credentials"
                  >
                    <Sparkles className="h-3 w-3" />
                    <span>Admin autofill</span>
                  </button>
                </div>

                {/* Primary Sign In Button (~52px height) */}
                <div className="pt-1.5">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="h-[52px] w-full py-3 px-5 rounded-2xl text-sm font-bold text-white bg-gradient-to-r from-[#4B46E5] via-[#6D3DF5] to-[#7C3AED] hover:from-indigo-500 hover:to-violet-500 active:scale-[0.99] disabled:opacity-70 disabled:cursor-not-allowed shadow-md hover:shadow-lg shadow-indigo-600/20 transition-all flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Signing In...</span>
                      </>
                    ) : (
                      <>
                        <span>Sign In</span>
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </div>

                {/* Subtle OR Divider */}
                <div className="relative flex items-center justify-center my-3.5">
                  <div className="w-full border-t border-slate-100 dark:border-slate-800/80" />
                  <span className="absolute px-2.5 bg-white dark:bg-[#0B0F19] text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    OR
                  </span>
                </div>

                {/* Security & Encryption Information Section */}
                <div className="rounded-2xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100/80 dark:border-indigo-900/40 p-3 flex items-center gap-3">
                  <div className="h-8 w-8 rounded-xl bg-white dark:bg-slate-900 border border-indigo-100 dark:border-indigo-800/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0 shadow-2xs">
                    <Shield className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-800 dark:text-slate-200 leading-tight">
                      Your session is encrypted and secure
                    </p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight mt-0.5">
                      We keep your data private and protected.
                    </p>
                  </div>
                </div>
              </form>
            </div>

            {/* Connected Platform Footer */}
            <p className="text-[11.5px] text-slate-400 dark:text-slate-500 text-center mt-3">
              NextRole Job Discovery Platform &copy; 2026
            </p>
          </div>
        </div>
      </main>

      {/* Invisible Bottom Spacing Anchor on Desktop */}
      <footer className="w-full max-w-[1340px] mx-auto hidden lg:block h-1 shrink-0" />
    </div>
  );
};

export default LoginPage;
