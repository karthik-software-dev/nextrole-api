import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  CheckSquare,
  Building2,
  Radar,
  Key,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Loader2,
  Save,
  ShieldCheck,
  User,
  Sliders,
} from 'lucide-react';
import { getSettings, updateSettings, testApifyToken } from '../api/settings';
import { useToast } from '../context/ToastContext';
import { Button } from '../components/ui/Button';

interface NavCard {
  label: string;
  path: string;
  icon: React.ElementType;
  description: string;
}

const navCards: NavCard[] = [
  {
    label: 'Job Feed',
    path: '/jobs',
    icon: Compass,
    description: 'Browse and filter job listings',
  },
  {
    label: 'Applications',
    path: '/applications',
    icon: CheckSquare,
    description: 'Track your application pipeline',
  },
  {
    label: 'Companies',
    path: '/companies',
    icon: Building2,
    description: 'Explore target companies',
  },
  {
    label: 'Discovery',
    path: '/discovery',
    icon: Radar,
    description: 'Discover new opportunities',
  },
];

export const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);

  // Profile Form State
  const [userName, setUserName] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [targetRole, setTargetRole] = useState('');

  // Search Scoring State
  const [minScore, setMinScore] = useState(8.0);
  const [minExp, setMinExp] = useState(1);
  const [maxExp, setMaxExp] = useState(5);
  const [locations, setLocations] = useState<string[]>([]);

  // Apify Integrations State
  const [apifyToken, setApifyToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [testResult, setTestResult] = useState<{
    valid: boolean;
    username?: string | null;
    message: string;
  } | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setIsLoading(true);
      const data = await getSettings();
      if (data.profile) {
        setUserName(data.profile.name || '');
        setUserEmail(data.profile.email || '');
        setTargetRole(data.profile.target_role || '');
      }
      if (data.scoring) {
        setMinScore(data.scoring.min_score || 8.0);
        setMinExp(data.scoring.min_experience || 1);
        setMaxExp(data.scoring.max_experience || 5);
        setLocations(data.scoring.target_locations || ['Bangalore', 'Chennai', 'Remote']);
      }
      if (data.integrations) {
        setApifyToken(data.integrations.apify_api_token || '');
        if (data.integrations.is_apify_configured) {
          setTestResult({
            valid: true,
            message: 'Token configured & saved',
          });
        }
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
      toast.error('Could not load current settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestApify = async () => {
    const trimmed = apifyToken.trim();
    if (!trimmed) {
      setTestResult({
        valid: false,
        message: 'Please paste your Apify API token first.',
      });
      return;
    }

    try {
      setIsTesting(true);
      setTestResult(null);
      const res = await testApifyToken(trimmed);
      setTestResult(res);
      if (res.valid) {
        toast.success(res.message || 'Apify token verified successfully!');
      } else {
        toast.error(res.message || 'Apify token validation failed');
      }
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || 'Failed to ping Apify API';
      setTestResult({
        valid: false,
        message: msg,
      });
      toast.error(msg);
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveAll = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSaving(true);
      await updateSettings({
        profile: {
          name: userName,
          email: userEmail,
          target_role: targetRole,
        },
        scoring: {
          min_score: minScore,
          min_experience: minExp,
          max_experience: maxExp,
          target_locations: locations,
        },
        integrations: {
          apify_api_token: apifyToken.trim(),
        },
      });
      toast.success('Settings and API token saved successfully!', 2000);
    } catch (err: any) {
      console.error('Failed to save settings:', err);
      toast.error(err.message || 'Failed to update settings');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-8 pb-16 max-w-6xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-[28px] sm:text-[32px] font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-3">
          <span>Settings & Configuration</span>
        </h1>
        <p className="mt-1 text-[13.5px] text-slate-700 dark:text-slate-400">
          Manage your candidate profile, scraper API tokens, and job scoring thresholds.
        </p>
      </div>

      {/* Quick Nav Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {navCards.map((card) => {
          const Icon = card.icon;
          return (
            <button
              key={card.path}
              onClick={() => navigate(card.path)}
              className="group flex flex-col items-center justify-center gap-2.5 p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] shadow-2xs hover:border-indigo-300 dark:hover:border-indigo-700/60 hover:shadow-xs transition-all duration-200 cursor-pointer"
            >
              <div className="h-10 w-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 flex items-center justify-center group-hover:bg-indigo-100 dark:group-hover:bg-indigo-900/60 transition-colors">
                <Icon className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div className="text-center">
                <p className="text-[17px] font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                  {card.label}
                </p>
                <p className="text-[13px] text-slate-700 dark:text-slate-400">
                  {card.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-400">
          <Loader2 className="h-7 w-7 animate-spin text-indigo-600" />
          <p className="text-[13.5px] font-medium">Loading configuration preferences...</p>
        </div>
      ) : (
        <form onSubmit={handleSaveAll} className="space-y-6">
          {/* SECTION 1: Scraper & API Integrations (Apify Token) */}
          <div className="rounded-2xl border border-indigo-200/90 dark:border-indigo-900/60 bg-white dark:bg-[#111726] p-6 sm:p-7 shadow-xs relative overflow-hidden">
            {/* Top Accent Gradient Bar */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-500" />

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200/60 dark:border-indigo-800/60 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0 shadow-xs">
                  <Key className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-[17px] font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>Scraper & Crawler API Integrations</span>
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[13px] font-bold bg-indigo-50 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300 border border-indigo-200/80 dark:border-indigo-800/80">
                      Apify Client
                    </span>
                  </h2>
                  <p className="text-[14px] text-slate-700 dark:text-slate-400 mt-0.5">
                    Connect your Apify account to power live scrapers for LinkedIn, Indeed, Naukri, and Wellfound.
                  </p>
                </div>
              </div>

              {/* Status Badge */}
              <div className="shrink-0">
                {testResult?.valid ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[13px] font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/70">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    <span>Connected & Active</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[13px] font-semibold bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                    <span className="h-2 w-2 rounded-full bg-slate-400" />
                    <span>Not Verified</span>
                  </span>
                )}
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-[17px] font-bold text-slate-800 dark:text-slate-200 mb-1.5">
                  Apify Personal API Token
                </label>
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
                  <div className="relative flex-1">
                    <input
                      type={showToken ? 'text' : 'password'}
                      value={apifyToken}
                      onChange={(e) => {
                        setApifyToken(e.target.value);
                        setTestResult(null);
                      }}
                      placeholder="apify_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      className="w-full h-11 px-4 pr-11 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-slate-800 text-[15.5px] font-mono text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-2xs transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowToken(!showToken)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
                      title={showToken ? 'Hide token' : 'Show token'}
                    >
                      {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>

                  {/* Verify Token Button */}
                  <button
                    type="button"
                    disabled={isTesting || !apifyToken.trim()}
                    onClick={handleTestApify}
                    className="h-11 px-4 rounded-xl text-[13.5px] font-bold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-750 text-slate-700 dark:text-slate-200 shadow-2xs hover:shadow-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer shrink-0"
                  >
                    {isTesting ? (
                      <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                    ) : (
                      <ShieldCheck className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    )}
                    <span>{isTesting ? 'Verifying...' : 'Verify Connection'}</span>
                  </button>
                </div>
              </div>

              {/* Real-Time Verification Alert Box */}
              {testResult && (
                <div
                  className={`p-3.5 rounded-xl border flex items-start gap-2.5 text-[12.5px] ${testResult.valid
                    ? 'bg-emerald-50/80 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-300'
                    : 'bg-rose-50/80 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800/60 text-rose-800 dark:text-rose-300'
                    }`}
                >
                  {testResult.valid ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <p className="font-bold">{testResult.valid ? 'Token Verified' : 'Verification Issue'}</p>
                    <p className="mt-0.5 leading-relaxed">{testResult.message}</p>
                  </div>
                </div>
              )}

              {/* Informational Footer with link */}
              <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[13px] text-slate-700 dark:text-slate-400">
                <p>
                  💡 <strong>Tip:</strong> Direct company ATS feeds (Greenhouse, Lever, SmartRecruiters) operate with zero cost without requiring an Apify key.
                </p>
                <a
                  href="https://console.apify.com/account/integrations"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[14px] font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 hover:underline shrink-0"
                >
                  <span>Get Free Token on Apify</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          </div>

          {/* SECTION 2: Candidate Profile & Target Role */}
          <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] p-6 sm:p-7 shadow-xs space-y-5">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
              <div className="h-10 w-10 rounded-xl bg-purple-50 dark:bg-purple-950/60 border border-purple-200/60 dark:border-purple-800/60 flex items-center justify-center text-purple-600 dark:text-purple-400 shrink-0 shadow-xs">
                <User className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-[17px] font-bold text-slate-900 dark:text-white">
                  Candidate Profile & Role Preferences
                </h2>
                <p className="text-[13px] text-slate-700 dark:text-slate-400 mt-0.5">
                  Your identity details and role keywords used for scoring and cover letters.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-[14px] font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  placeholder="Karthik Software Dev"
                  className="w-full h-10 px-3.5 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-slate-800 text-[14px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[14px] font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder="karthik@example.com"
                  className="w-full h-10 px-3.5 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-slate-800 text-[14px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[14px] font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Target Role Keyword
                </label>
                <input
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="Python Backend Engineer"
                  className="w-full h-10 px-3.5 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-slate-800 text-[14px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* SECTION 3: Search Calibration & Experience Filter */}
          <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-[#111726] p-6 sm:p-7 shadow-xs space-y-5">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
              <div className="h-10 w-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/60 dark:border-emerald-800/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0 shadow-xs">
                <Sliders className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-[17px] font-bold text-slate-900 dark:text-white">
                  Job Match & Experience Thresholds
                </h2>
                <p className="text-[13px] text-slate-700 dark:text-slate-400 mt-0.5">
                  Control which opportunities qualify for Tier-1 and pass the discovery filter.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-[14px] font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Min Experience (Years)
                </label>
                <input
                  type="number"
                  min="0"
                  max="20"
                  value={minExp}
                  onChange={(e) => setMinExp(Number(e.target.value))}
                  className="w-full h-10 px-3.5 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-slate-800 text-[14px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[14px] font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Max Experience (Years)
                </label>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={maxExp}
                  onChange={(e) => setMaxExp(Number(e.target.value))}
                  className="w-full h-10 px-3.5 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-slate-800 text-[14px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[14px] font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Min Score Threshold
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max="50"
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="w-full h-10 px-3.5 rounded-xl bg-slate-50 dark:bg-[#0B0F17] border border-slate-200 dark:border-slate-800 text-[13.5px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Bottom Save Bar */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              leftIcon={isSaving ? <Loader2 className="h-4 w-4 animate-spin text-white" /> : <Save className="h-4 w-4 text-white" />}
              disabled={isSaving}
              className="shadow-md hover:shadow-indigo-500/25 px-7 cursor-pointer"
            >
              <span>{isSaving ? 'Saving Changes...' : 'Save Configuration'}</span>
            </Button>
          </div>
        </form>
      )}
    </div>
  );
};

export default SettingsPage;
