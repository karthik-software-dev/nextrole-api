import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ChevronRight, Flame, MapPin, Globe } from 'lucide-react';
import { CompanyAvatar } from '../ui/CompanyAvatar';
import type { TopHiringCompany } from '../../types';

interface TopHiringCompaniesCardProps {
  companies?: TopHiringCompany[];
}

export const TopHiringCompaniesCard: React.FC<TopHiringCompaniesCardProps> = ({ companies }) => {
  const navigate = useNavigate();

  const companyList: TopHiringCompany[] = companies || [];

  return (
    <div className="flex flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-[#111726]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4.5 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <Flame className="h-4 w-4 fill-amber-500/20" />
          </div>
          <div>
            <h3 className="text-[17px] font-bold tracking-tight text-slate-900 dark:text-white">
              Hiring Velocity Leaderboard
            </h3>
            <p className="text-[11.5px] text-slate-500 dark:text-slate-400">
              Top companies aggressively recruiting in this period
            </p>
          </div>
        </div>

        <Link
          to="/companies"
          className="group inline-flex items-center gap-1 text-[13px] font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 transition-colors"
        >
          <span>View All</span>
          <ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>

      {/* List Body */}
      <div className="flex-1 divide-y divide-slate-100 dark:divide-slate-800/80 p-3 sm:p-4">
        {companyList.length === 0 ? (
          <div className="flex min-h-[220px] items-center justify-center text-xs text-slate-400">
            No company hiring activity recorded in this period.
          </div>
        ) : (
          companyList.map((company, index) => {
          const rank = index + 1;
          const isSpree = company.job_count >= 6;

          return (
            <div
              key={company.name}
              onClick={() => navigate(`/jobs?company=${encodeURIComponent(company.name)}`)}
              className="group flex items-center justify-between p-3 rounded-xl hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3 min-w-0">
                {/* Rank Badge */}
                <span className={`flex h-6 w-6 items-center justify-center rounded-lg text-[11px] font-extrabold shrink-0 ${
                  rank === 1
                    ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-300 dark:border-amber-700/60'
                    : rank === 2
                    ? 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                    : rank === 3
                    ? 'bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-500'
                    : 'bg-slate-100 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400'
                }`}>
                  #{rank}
                </span>

                <CompanyAvatar name={company.name} size="sm" />

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[13.5px] font-bold text-slate-900 dark:text-white truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {company.name}
                    </span>
                    {isSpree && (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                        <Flame className="h-2.5 w-2.5 fill-current" />
                        Hiring Spree
                      </span>
                    )}
                  </div>

                  <div className="mt-0.5 flex items-center gap-2 text-[11.5px] text-slate-500 dark:text-slate-400">
                    {company.is_remote && (
                      <span className="flex items-center gap-0.5">
                        <Globe className="h-3 w-3 text-emerald-500" />
                        <span>Remote</span>
                      </span>
                    )}
                    {company.locations.length > 0 && (
                      <span className="flex items-center gap-0.5 truncate">
                        <MapPin className="h-3 w-3 text-slate-400" />
                        <span>{company.locations.join(' · ')}</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Open Roles Pill */}
              <div className="flex items-center gap-2 shrink-0">
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-bold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-400 border border-indigo-200/80 dark:border-indigo-800/80 shadow-2xs">
                  <span>{company.job_count} Roles</span>
                </span>
                <ChevronRight className="h-4 w-4 text-slate-300 dark:text-slate-600 group-hover:text-slate-500 dark:group-hover:text-slate-400 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>
          );
        })
      )}
      </div>
    </div>
  );
};

export default TopHiringCompaniesCard;
