import React, { useState } from 'react';
import {
  Sliders,
  Building2,
  Clock,
  User,
  CheckCircle2,
  Plus,
  X,
  Save,
  Shield,
  Briefcase,
  MapPin,
  Sparkles,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useToast } from '../context/ToastContext';

export const SettingsPage: React.FC = () => {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<'preferences' | 'companies' | 'discovery' | 'profile'>('preferences');

  // Job Preferences state
  const [targetTitles, setTargetTitles] = useState<string[]>([
    'Lead Backend Engineer',
    'Senior Python Engineer',
    'Python Tech Lead',
    'Staff Software Engineer',
  ]);
  const [newTitle, setNewTitle] = useState('');

  const [skills, setSkills] = useState<string[]>([
    'Python',
    'FastAPI',
    'PostgreSQL',
    'Redis',
    'Docker',
    'System Design',
    'Distributed Systems',
    'Microservices',
    'AWS',
  ]);
  const [newSkill, setNewSkill] = useState('');

  const [targetLocations, setTargetLocations] = useState<string[]>(['Bangalore', 'Chennai', 'Remote']);
  const [minExp, setMinExp] = useState(4);
  const [maxExp, setMaxExp] = useState(9);

  // Target Companies state
  const [targetCompanies, setTargetCompanies] = useState<string[]>([
    'Razorpay',
    'Zepto',
    'Cred',
    'Swiggy',
    'Groww',
    'Cisco',
    'Google',
    'Zoho',
    'Atlassian',
    'Urban Company',
  ]);
  const [newCompany, setNewCompany] = useState('');

  // Profile state
  const [name, setName] = useState('Arun Kumar');
  const [email, setEmail] = useState('arun.kumar@example.com');
  const [currentRole, setCurrentRole] = useState('Lead Backend Engineer');
  const [resumeVersion, setResumeVersion] = useState('Resume_ArunKumar_Backend_Lead_2026.pdf');

  // Discovery settings
  const [cronFreq, setCronFreq] = useState('every_4_hours');
  const [relevanceThreshold, setRelevanceThreshold] = useState(50);

  const handleAddTitle = () => {
    if (newTitle.trim() && !targetTitles.includes(newTitle.trim())) {
      setTargetTitles([...targetTitles, newTitle.trim()]);
      setNewTitle('');
    }
  };

  const handleRemoveTitle = (t: string) => {
    setTargetTitles(targetTitles.filter((item) => item !== t));
  };

  const handleAddSkill = () => {
    if (newSkill.trim() && !skills.includes(newSkill.trim())) {
      setSkills([...skills, newSkill.trim()]);
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (s: string) => {
    setSkills(skills.filter((item) => item !== s));
  };

  const handleAddCompany = () => {
    if (newCompany.trim() && !targetCompanies.includes(newCompany.trim())) {
      setTargetCompanies([...targetCompanies, newCompany.trim()]);
      setNewCompany('');
    }
  };

  const handleRemoveCompany = (c: string) => {
    setTargetCompanies(targetCompanies.filter((item) => item !== c));
  };

  const handleSave = () => {
    toast.success('Settings saved successfully', 1800);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            System & User Settings
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Configure job discovery criteria, scoring weights, target companies, and personal profile.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="primary" size="sm" leftIcon={<Save className="h-4 w-4" />} onClick={handleSave}>
            Save Changes
          </Button>
        </div>
      </div>

      {/* Settings Navigation Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-800 flex gap-6">
        {[
          { id: 'preferences', label: 'Job Preferences', icon: Briefcase },
          { id: 'companies', label: 'Target Companies', icon: Building2 },
          { id: 'discovery', label: 'Discovery Engine', icon: Sliders },
          { id: 'profile', label: 'User Profile', icon: User },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors cursor-pointer ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab: Job Preferences */}
      {activeTab === 'preferences' && (
        <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs space-y-6">
          {/* Target Job Titles */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
              Target Job Titles (Auto-Scored)
            </label>
            <div className="flex flex-wrap gap-2 mb-3">
              {targetTitles.map((title) => (
                <span
                  key={title}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
                >
                  {title}
                  <button
                    onClick={() => handleRemoveTitle(title)}
                    className="hover:text-rose-500 cursor-pointer"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2 max-w-md">
              <input
                type="text"
                placeholder="Add new target title (e.g. Principal Architect)..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTitle())}
                className="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
              />
              <Button variant="secondary" size="sm" onClick={handleAddTitle}>
                <Plus className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {/* Core Target Skills */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
              Core Skills & Keywords
            </label>
            <div className="flex flex-wrap gap-2 mb-3">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                >
                  {skill}
                  <button
                    onClick={() => handleRemoveSkill(skill)}
                    className="hover:text-rose-500 cursor-pointer"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2 max-w-md">
              <input
                type="text"
                placeholder="Add skill (e.g. Kubernetes, Kafka)..."
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSkill())}
                className="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
              />
              <Button variant="secondary" size="sm" onClick={handleAddSkill}>
                <Plus className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {/* Experience Range */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-4 max-w-md">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
                Min Experience (Years)
              </label>
              <input
                type="number"
                value={minExp}
                onChange={(e) => setMinExp(Number(e.target.value))}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
                Max Experience (Years)
              </label>
              <input
                type="number"
                value={maxExp}
                onChange={(e) => setMaxExp(Number(e.target.value))}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* Tab: Target Companies */}
      {activeTab === 'companies' && (
        <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs space-y-5">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Target Company Whitelist
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Jobs from these companies automatically receive +15 priority points and Tier 1 eligibility.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {targetCompanies.map((c) => (
              <span
                key={c}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800"
              >
                ★ {c}
                <button
                  onClick={() => handleRemoveCompany(c)}
                  className="hover:text-rose-500 cursor-pointer"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>

          <div className="flex gap-2 max-w-md pt-3 border-t border-slate-100 dark:border-slate-800">
            <input
              type="text"
              placeholder="Add target company name..."
              value={newCompany}
              onChange={(e) => setNewCompany(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCompany())}
              className="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            />
            <Button variant="secondary" size="sm" onClick={handleAddCompany}>
              Add Target
            </Button>
          </div>
        </div>
      )}

      {/* Tab: Discovery Engine */}
      {activeTab === 'discovery' && (
        <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs space-y-6">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Scheduled Sync Frequency
            </label>
            <select
              value={cronFreq}
              onChange={(e) => setCronFreq(e.target.value)}
              className="w-full max-w-md bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="every_2_hours">Every 2 Hours (Aggressive)</option>
              <option value="every_4_hours">Every 4 Hours (Recommended)</option>
              <option value="daily">Once Daily at 08:00 IST</option>
              <option value="manual">Manual Execution Only</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Minimum Relevance Score Threshold ({relevanceThreshold}%)
            </label>
            <input
              type="range"
              min={30}
              max={80}
              value={relevanceThreshold}
              onChange={(e) => setRelevanceThreshold(Number(e.target.value))}
              className="w-full max-w-md accent-indigo-600"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Jobs with relevance score below {relevanceThreshold}% are dropped before reaching PostgreSQL.
            </p>
          </div>
        </div>
      )}

      {/* Tab: User Profile */}
      {activeTab === 'profile' && (
        <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 shadow-xs space-y-4 max-w-md">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Full Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Current Title / Seniority
            </label>
            <input
              type="text"
              value={currentRole}
              onChange={(e) => setCurrentRole(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
              Default Resume Tag
            </label>
            <input
              type="text"
              value={resumeVersion}
              onChange={(e) => setResumeVersion(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>
      )}
    </div>
  );
};
