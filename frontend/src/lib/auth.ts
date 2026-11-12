/**
 * Authentication utilities for the FastAPI-compatible authentication system
 */

import { useEffect, useState } from 'react';
import { getBackendUrl } from './utils';
import { clearAuthStorage, isTokenExpired, setAuthCookie } from './session';

// Mock auth client implementation for compatibility
// This is kept to maintain compatibility with existing code that imports from this file
const mockAuthClient = {
  useSession: () => ({ data: null, isPending: true, error: null, status: 'loading' }),
  getSession: async () => {
    // Check if we're in the browser
    if (typeof window === 'undefined') {
      return { data: null };
    }

    const token = localStorage.getItem('auth_token');
    const userData = localStorage.getItem('user');

    let user = null;
    if (userData) {
      try {
        user = JSON.parse(userData);
      } catch (e) {
        console.error('Failed to parse user data:', e);
      }
    }

    return {
      data: token ? { user, token } : null
    };
  },
  signIn: {
    email: async ({ email, password, callbackURL }: { email: string; password: string; callbackURL?: string }) => {
      try {
        // Make actual API call to login
        const response = await fetch(`${getBackendUrl()}/api/token`, {
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
          const errorData = await response.json();
          return { error: { message: errorData.detail || 'Login failed' } };
        }

        const data = await response.json();

        // Store token + middleware cookie (mobile path logs in via a full
        // page navigation, so the proxy needs the cookie too)
        localStorage.setItem('auth_token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token);
        }
        setAuthCookie(data.access_token);

        // Get user info
        const userResponse = await fetch(`${getBackendUrl()}/api/me`, {
          headers: {
            'Authorization': `Bearer ${data.access_token}`,
          },
        });

        let userData = null;
        if (userResponse.ok) {
          userData = await userResponse.json();
          localStorage.setItem('user', JSON.stringify(userData));
        }

        // Redirect if callbackURL is provided
        if (callbackURL) {
          window.location.href = callbackURL;
        }

        return { data: { user: userData, token: data.access_token } };
      } catch (error) {
        return { error: { message: (error as Error).message || 'Login failed' } };
      }
    }
  },
  signUp: {
    email: async ({ email, password, name, callbackURL }: { email: string; password: string; name?: string; callbackURL?: string }) => {
      try {
        // Register the user
        const registerResponse = await fetch(`${getBackendUrl()}/api/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email,
            password,
            username: name || email.split('@')[0],
            full_name: name || email.split('@')[0],
          }),
        });

        if (!registerResponse.ok) {
          const errorData = await registerResponse.json();
          return { error: { message: errorData.detail || 'Registration failed' } };
        }

        // Auto-login after registration
        const loginResult = await mockAuthClient.signIn.email({ email, password, callbackURL });
        return loginResult;
      } catch (error) {
        return { error: { message: (error as Error).message || 'Registration failed' } };
      }
    }
  },
  signOut: async () => {
    try {
      // Clear auth data (localStorage + middleware cookie)
      clearAuthStorage();

      // Redirect to login
      window.location.href = '/auth/login';

      return { success: true };
    } catch (error) {
      return { error: { message: (error as Error).message || 'Logout failed' } };
    }
  }
};

// Export the mock auth client for compatibility
export const authClient = mockAuthClient;

// Export individual functions for direct use
export const signIn = mockAuthClient.signIn;
export const signUp = mockAuthClient.signUp;
export const signOut = mockAuthClient.signOut;

// Reactive session hook. MUST be a real hook (useState/useEffect): the old
// synchronous version returned `isPending: true` during SSR and `false` on
// the client's first render, so the root page's Initialization_Status card
// never matched between server and client — a hydration mismatch that left
// the card stuck on screen until a hard refresh.
interface SessionState {
  data: { user: unknown; token: string } | null;
  isPending: boolean;
  error: Error | null;
  status: 'loading' | 'authenticated' | 'unauthenticated';
}

export const useSession = (): SessionState => {
  // Same initial value on server AND client first render → hydration matches.
  const [state, setState] = useState<SessionState>({
    data: null,
    isPending: true,
    error: null,
    status: 'loading',
  });

  useEffect(() => {
    const read = () => {
      const token = localStorage.getItem('auth_token');
      if (token && !isTokenExpired(token)) {
        let user = null;
        const userData = localStorage.getItem('user');
        if (userData) {
          try {
            user = JSON.parse(userData);
          } catch (e) {
            console.error('Failed to parse user data:', e);
          }
        }
        setState({ data: { user, token }, isPending: false, error: null, status: 'authenticated' });
      } else {
        setState({ data: null, isPending: false, error: null, status: 'unauthenticated' });
      }
    };

    read();
    // Another tab signed out / signed in — stay in sync.
    const onStorage = (e: StorageEvent) => {
      if (e.key === null || e.key === 'auth_token') read();
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  return state;
};