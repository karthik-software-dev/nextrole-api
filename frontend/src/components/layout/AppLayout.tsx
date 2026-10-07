import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopHeader } from './TopHeader';
import { DiscoveryModal } from '../discovery/DiscoveryModal';

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const [isMobileNavOpen, setIsMobileNavOpen] = React.useState(false);

  // Auto-close mobile navigation when navigating to a new route
  React.useEffect(() => {
    setIsMobileNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 transition-colors">
      {/* Navigation Sidebar (Desktop persistent + Mobile slide-over drawer) */}
      <Sidebar
        isMobileOpen={isMobileNavOpen}
        onMobileClose={() => setIsMobileNavOpen(false)}
      />

      {/* Main App Container */}
      <div className="flex-1 flex flex-col min-w-0 w-full overflow-x-hidden">
        <TopHeader onToggleMobileNav={() => setIsMobileNavOpen((prev) => !prev)} />

        <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl w-full mx-auto overflow-x-hidden">
          <div key={location.pathname} className="page-reveal">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Global Teams-Style Discovery Loading Modal */}
      <DiscoveryModal />
    </div>
  );
};

