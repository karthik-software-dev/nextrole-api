import React, { createContext, useContext, useEffect, useState } from 'react';
import type { AuthUser, LoginRequest } from '../api/auth';
import { loginApi, getMeApi, logoutApi } from '../api/auth';


interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  logout: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('nextrole_token'));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem('nextrole_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const verifyAuth = async () => {
      const storedToken = localStorage.getItem('nextrole_token');
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const currentUser = await getMeApi();
        if (isMounted) {
          setUser(currentUser);
          setToken(storedToken);
          localStorage.setItem('nextrole_user', JSON.stringify(currentUser));
        }
      } catch (err) {
        console.warn('Authentication token verification failed:', err);
        if (isMounted) {
          localStorage.removeItem('nextrole_token');
          localStorage.removeItem('nextrole_user');
          setToken(null);
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    verifyAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (credentials: LoginRequest) => {
    const res = await loginApi(credentials);
    localStorage.setItem('nextrole_token', res.access_token);
    localStorage.setItem('nextrole_user', JSON.stringify(res.user));
    setToken(res.access_token);
    setUser(res.user);
  };

  const logout = () => {
    logoutApi().catch(() => {});
    localStorage.removeItem('nextrole_token');
    localStorage.removeItem('nextrole_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
