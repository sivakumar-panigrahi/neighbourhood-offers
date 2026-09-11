import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi } from '../api/auth';
import { clearStoredToken, getStoredToken, setStoredToken } from '../utils/authStorage';
import type { User, UserRole } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, role: UserRole) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<User | null>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  const logout = useCallback(() => {
    clearStoredToken();
    setToken(null);
    setUser(null);
    setError(null);
  }, []);

  const refreshUser = useCallback(async (): Promise<User | null> => {
    const currentToken = getStoredToken();
    if (!currentToken) {
      setUser(null);
      setToken(null);
      return null;
    }
    try {
      const profile = await authApi.getCurrentUser();
      setUser(profile);
      setToken(currentToken);
      return profile;
    } catch (err: any) {
      console.warn('Session verification failed, logging out', err);
      logout();
      return null;
    }
  }, [logout]);

  // Initial session restoration
  useEffect(() => {
    let isMounted = true;

    const initAuth = async () => {
      const stored = getStoredToken();
      if (!stored) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const profile = await authApi.getCurrentUser();
        if (isMounted) {
          setUser(profile);
          setToken(stored);
        }
      } catch (err) {
        if (isMounted) {
          logout();
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    initAuth();

    // Listen for 401 unauthorized events emitted from client.ts
    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);

    return () => {
      isMounted = false;
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, [logout]);

  const login = async (email: string, password: string): Promise<User> => {
    setIsLoading(true);
    setError(null);
    try {
      const tokenResponse = await authApi.login(email, password);
      setStoredToken(tokenResponse.access_token);
      setToken(tokenResponse.access_token);

      const profile = await authApi.getCurrentUser();
      setUser(profile);
      return profile;
    } catch (err: any) {
      const msg = err.message || 'Login failed. Please check your credentials.';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, role: UserRole): Promise<User> => {
    setIsLoading(true);
    setError(null);
    try {
      const newUser = await authApi.register(email, password, role);
      // Auto-login after registration for seamless UX
      await login(email, password);
      return newUser;
    } catch (err: any) {
      const msg = err.message || 'Registration failed. Please check your details.';
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isLoading,
    error,
    login,
    register,
    logout,
    refreshUser,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
