'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { getBackendUrl } from '../lib/utils';

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

  useEffect(() => {
    // Check for stored token on initial load
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('user');

    if (storedToken) {
      setToken(storedToken);

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
              // Token is invalid, clear it
              localStorage.removeItem('auth_token');
              localStorage.removeItem('user');
              setToken(null);
              setUser(null);
            }
          } catch (error) {
            console.error('Failed to fetch user info:', error);
            // Clear token if there's an error
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user');
            setToken(null);
            setUser(null);
          }
        };

        fetchUserInfo();
      }
    }

    setLoading(false);
  }, []);

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
      
      // Set cookie for middleware
      if (typeof document !== 'undefined') {
        document.cookie = `auth_token=${accessToken}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
      }

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

      // Set up token refresh (using default expiration if not provided)
      const expiresAt = data.expires_at || new Date(Date.now() + 30 * 60 * 1000).toISOString(); // Default to 30 mins from now
      scheduleTokenRefresh(expiresAt);
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
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    
    // Clear cookie for middleware
    if (typeof document !== 'undefined') {
      document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }
    
    router.push('/auth/login'); // Redirect to login page
  };

  const refreshToken = async (): Promise<boolean> => {
    const refreshTokenStored = localStorage.getItem('refresh_token');

    if (!refreshTokenStored) {
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
        // Try to parse as JSON, but handle cases where response is not JSON
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          // If response is not JSON, try to get text or use default message
          try {
            const errorText = await response.text();
            throw new Error(errorText || `Token refresh failed with status ${response.status}`);
          } catch {
            // If we can't read the response at all, throw a generic error
            throw new Error(`Token refresh failed with status ${response.status}`);
          }
        }
        throw new Error(errorData.detail || errorData.message || 'Token refresh failed');
      }

      const data = await response.json();
      const newAccessToken = data.access_token;

      setToken(newAccessToken);
      localStorage.setItem('auth_token', newAccessToken);

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

      scheduleTokenRefresh(data.expires_at);
      return true;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        // Network error - logout user
        console.error('Network error during token refresh:', error);
        logout();
        return false;
      }
      console.error('Token refresh failed:', error);
      logout();
      return false;
    }
  };

  const scheduleTokenRefresh = (expiresAt: string) => {
    // Calculate time until token expires (subtract 5 minutes as buffer)
    const expiryTime = new Date(expiresAt).getTime();
    const currentTime = Date.now();
    const timeUntilExpiry = expiryTime - currentTime - (5 * 60 * 1000); // 5 minutes before expiry

    if (timeUntilExpiry > 0) {
      setTimeout(() => {
        refreshToken();
      }, timeUntilExpiry);
    }
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token,
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