import React, { createContext, useContext, useEffect, useState } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system';
export type ActiveTheme = 'light' | 'dark';

interface ThemeContextType {
  theme: ActiveTheme;
  themeMode: ThemeMode;
  toggleTheme: () => void;
  setThemeMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  themeMode: 'system',
  toggleTheme: () => {},
  setThemeMode: () => {},
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('careerpilot_theme_mode');
    if (saved === 'dark' || saved === 'light' || saved === 'system') return saved;
    const legacy = localStorage.getItem('careerpilot_theme');
    if (legacy === 'dark' || legacy === 'light') return legacy;
    return 'system';
  });

  const getSystemTheme = (): ActiveTheme => {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  };

  const [activeTheme, setActiveTheme] = useState<ActiveTheme>(() => {
    if (themeMode === 'system') return getSystemTheme();
    return themeMode;
  });

  useEffect(() => {
    const computedTheme: ActiveTheme = themeMode === 'system' ? getSystemTheme() : themeMode;
    setActiveTheme(computedTheme);

    const root = document.documentElement;
    if (computedTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    localStorage.setItem('careerpilot_theme_mode', themeMode);
    localStorage.setItem('careerpilot_theme', computedTheme);

    if (themeMode === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e: MediaQueryListEvent) => {
        const newTheme: ActiveTheme = e.matches ? 'dark' : 'light';
        setActiveTheme(newTheme);
        if (newTheme === 'dark') {
          root.classList.add('dark');
        } else {
          root.classList.remove('dark');
        }
        localStorage.setItem('careerpilot_theme', newTheme);
      };

      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [themeMode]);

  const toggleTheme = () => {
    setThemeModeState((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      return next;
    });
  };

  const setThemeMode = (mode: ThemeMode) => {
    setThemeModeState(mode);
  };

  return (
    <ThemeContext.Provider value={{ theme: activeTheme, themeMode, toggleTheme, setThemeMode }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
