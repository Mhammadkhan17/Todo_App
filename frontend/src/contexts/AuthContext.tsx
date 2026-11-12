'use client';

import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { getBackendUrl } from '../lib/utils';
import {
  clearAuthStorage,
  isTokenExpired,
  parseJwtExp,
  redirectToLogin,
  setAuthCookie,
} from '../lib/session';

interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Check for stored token on initial load
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('user');

    if (storedToken) {
      if (isTokenExpired(storedToken)) {
        // Token already expired while the app was closed: tear down so the
        // current page's auth gate redirects to sign-in.
        clearAuthStorage();
        setLoading(false);
        return;
      }

      setToken(storedToken);
      scheduleTokenRefresh(storedToken);

      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch (error) {
          console.error('Failed to parse stored user:', error);
          localStorage.removeItem('user'); // Remove corrupted user data
        }
      } else {
        // If we have a token but no user, fetch user info
        const fetchUserInfo = async () => {
          try {
            const response = await fetch(`${getBackendUrl()}/api/me`, {
              headers: {
                'Authorization': `Bearer ${storedToken}`,
              },
            });

            if (response.ok) {
              const userData = await response.json();
              setUser(userData);
              localStorage.setItem('user', JSON.stringify(userData));
            } else {
              // Token is invalid, clear it (localStorage + cookie)
              clearAuthStorage();
              setToken(null);
              setUser(null);
            }
          } catch (error) {
            console.error('Failed to fetch user info:', error);
            // Clear token if there's an error
            clearAuthStorage();
            setToken(null);
            setUser(null);
          }
        };

        fetchUserInfo();
      }
    }

    setLoading(false);
    // Runs once on mount: arms the proactive refresh timer for this page load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Session watchdog: expiry must sign the user out with NO interaction.
  // An idle page never fires a request (so no 401 can trigger the axios
  // interceptor) — this interval plus focus/visibility checks catches
  // expiry while the tab sits open, including laptop sleep/wake.
  useEffect(() => {
    if (!token) return;

    const check = () => {
      if (isTokenExpired(token)) {
        clearAuthStorage();
        setToken(null);
        setUser(null);
        redirectToLogin();
      }
    };

    const interval = window.setInterval(check, 10_000);
    const onVisibility = () => {
      if (!document.hidden) check();
    };
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('focus', check);

    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('focus', check);
    };
  }, [token]);

  const login = async (email: string, password: string) => {
    try {
      const backendUrl = getBackendUrl();
      console.log('Attempting login to backend:', backendUrl); // Debug log

      const response = await fetch(`${backendUrl}/api/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: email,
          password: password,
        }),
      });

      if (!response.ok) {
        // Try to parse as JSON, but handle cases where response is not JSON
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          // If response is not JSON, try to get text or use default message
          try {
            const errorText = await response.text();
            throw new Error(errorText || `Login failed with status ${response.status}`);
          } catch {
            // If we can't read the response at all, throw a generic error
            throw new Error(`Login failed with status ${response.status}`);
          }
        }
        throw new Error(errorData.detail || errorData.message || 'Login failed');
      }

      const data = await response.json();

      // Store token and user info
      const accessToken = data.access_token;
      setToken(accessToken);
      localStorage.setItem('auth_token', accessToken);
      // The refresh pipeline is only alive if we persist the refresh token —
      // without it scheduleTokenRefresh used to fire into a dead end.
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      // Cookie for the Next proxy, lifetime aligned with the access token.
      setAuthCookie(accessToken);

      // Get user info
      const userResponse = await fetch(`${getBackendUrl()}/api/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
      }

      scheduleTokenRefresh(accessToken);
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        // Network error
        throw new Error('Network error: Unable to connect to the server. Please check your internet connection and ensure the backend server is running.');
      }
      throw error;
    }
  };

  const register = async (email: string, password: string, username: string, fullName?: string) => {
    try {
      const backendUrl = getBackendUrl();
      console.log('Attempting registration to backend:', backendUrl); // Debug log

      const response = await fetch(`${backendUrl}/api/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          username,
          full_name: fullName || username,
        }),
      });

      if (!response.ok) {
        // Try to parse as JSON, but handle cases where response is not JSON
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          // If response is not JSON, try to get text or use default message
          try {
            const errorText = await response.text();
            throw new Error(errorText || `Registration failed with status ${response.status}`);
          } catch {
            // If we can't read the response at all, throw a generic error
            throw new Error(`Registration failed with status ${response.status}`);
          }
        }
        throw new Error(errorData.detail || errorData.message || 'Registration failed');
      }

      // Auto-login after registration
      await login(email, password);
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        // Network error
        throw new Error('Network error: Unable to connect to the server. Please check your internet connection and ensure the backend server is running.');
      }
      throw error;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    clearAuthStorage(); // localStorage + middleware cookie
    router.push('/auth/login'); // Redirect to login page
  };

  const refreshToken = async (): Promise<boolean> => {
    const refreshTokenStored = localStorage.getItem('refresh_token');
    const currentAccessToken = localStorage.getItem('auth_token');

    if (!refreshTokenStored || isTokenExpired(currentAccessToken)) {
      // No refresh token and the access token is gone: session is over.
      // (Missing refresh token with a still-valid access token: do nothing —
      // the watchdog signs out at real expiry instead of dying silently.)
      if (isTokenExpired(currentAccessToken)) {
        clearAuthStorage();
        setToken(null);
        setUser(null);
        redirectToLogin();
      }
      return false;
    }

    try {
      const response = await fetch(`${getBackendUrl()}/api/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshTokenStored }),
      });

      if (!response.ok) {
        // Refresh failed but the access token may still be valid — stay
        // signed in until it actually expires (watchdog will finish the job).
        if (isTokenExpired(currentAccessToken)) {
          clearAuthStorage();
          setToken(null);
          setUser(null);
          redirectToLogin();
        }
        return false;
      }

      const data = await response.json();
      const newAccessToken = data.access_token as string | undefined;
      if (!newAccessToken) {
        return false;
      }

      setToken(newAccessToken);
      localStorage.setItem('auth_token', newAccessToken);
      // Backend omits refresh tokens on refresh responses — only overwrite
      // when a new one was actually issued.
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      setAuthCookie(newAccessToken);

      // Update user info
      const userResponse = await fetch(`${getBackendUrl()}/api/me`, {
        headers: {
          'Authorization': `Bearer ${newAccessToken}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
      }

      scheduleTokenRefresh(newAccessToken);
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      // Network/server hiccup: only end the session if the access token
      // itself has expired — otherwise keep the user in until real expiry.
      if (isTokenExpired(currentAccessToken)) {
        clearAuthStorage();
        setToken(null);
        setUser(null);
        redirectToLogin();
      }
      return false;
    }
  };

  // Schedule a proactive refresh 5 minutes before the access token expires.
  // Expiry itself comes from the JWT `exp` claim (UTC seconds) — never from
  // the backend's naive `expires_at` string, which JS would parse as local time.
  const scheduleTokenRefresh = (accessToken: string) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);

    const expMs = parseJwtExp(accessToken);
    if (!expMs) return;

    // 5 minutes before expiry
    const timeUntilRefresh = expMs - Date.now() - 5 * 60 * 1000;
    if (timeUntilRefresh > 0) {
      refreshTimerRef.current = setTimeout(() => {
        refreshToken();
      }, timeUntilRefresh);
    }
    // If refresh never happens, the 10s watchdog signs out at real expiry.
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token && !isTokenExpired(token),
    loading,
    login,
    register,
    logout,
    refreshToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}