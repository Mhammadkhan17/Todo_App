/**
 * Authentication utilities for the FastAPI-compatible authentication system
 */

import { getBackendUrl } from './utils';

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

        // Store token
        localStorage.setItem('auth_token', data.access_token);

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
      // Clear auth data
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');

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

// Compatibility exports for useSession hook
export const useSession = () => {
  // Check if we're in the browser (client-side)
  if (typeof window === 'undefined') {
    return {
      data: null,
      isPending: true,
      error: null,
      status: 'loading'
    };
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
    data: token ? { user, token } : null,
    isPending: false,
    error: null,
    status: token ? 'authenticated' : 'unauthenticated'
  };
};