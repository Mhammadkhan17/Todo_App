'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { User } from '@/types';
import { useAuth as useNewAuth } from '@/contexts/AuthContext'; // Use the new AuthContext
import { authApi } from '@/lib/api'; // Use the new API client

interface UseAuthReturn {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  register: (data: { email: string; password: string; name?: string }) => Promise<void>;
  logout: () => void;
  resetPassword: (data: { email: string }) => Promise<void>;
  clearError: () => void;
}

export function useAuth(): UseAuthReturn {
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  // Use the new AuthContext
  const { user, token, loading, login: contextLogin, register: contextRegister, logout: contextLogout } = useNewAuth();

  const isAuthenticated = !!token && !loading;

  const login = async (credentials: { email: string; password: string }) => {
    setIsLoading(true);
    setError(null);

    try {
      await contextLogin(credentials.email, credentials.password);
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: { email: string; password: string; name?: string }) => {
    setIsLoading(true);
    setError(null);

    try {
      await contextRegister(data.email, data.password, data.name || data.email.split('@')[0], data.name);
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    contextLogout();
    router.push('/auth/login');
  };

  const resetPassword = async (data: { email: string }) => {
    setIsLoading(true);
    setError(null);

    try {
      // Use the new API client for password reset
      await authApi.requestPasswordReset(data.email);
      setError('Password reset email sent successfully');
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'Failed to send password reset email');
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  return {
    user: user,
    isAuthenticated,
    isLoading: loading || isLoading,
    error,
    login,
    register,
    logout,
    resetPassword,
    clearError,
  };
}