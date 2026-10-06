/**
 * Session validation utility for enhanced security
 */

import { authClient } from '@/lib/auth';

/**
 * Validates the current session on the server side
 * @returns boolean indicating if session is valid
 */
export async function validateSession(): Promise<boolean> {
  try {
    const session = await authClient.getSession();
    return !!session?.data;
  } catch {
    // Don't log sensitive error details that could expose internal information
    console.error('Session validation failed');
    return false;
  }
}

/**
 * Checks if the user is authenticated by validating the session
 * @returns boolean indicating if user is authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  try {
    const session = await authClient.getSession();
    return !!session?.data?.user;
  } catch {
    // Don't log sensitive error details that could expose internal information
    console.error('Authentication check failed');
    return false;
  }
}

/**
 * Gets the current user from the session
 * @returns User object or null if not authenticated
 */
export async function getCurrentUser() {
  try {
    const session = await authClient.getSession();
    return session?.data?.user || null;
  } catch {
    // Don't log sensitive error details that could expose internal information
    console.error('Getting current user failed');
    return null;
  }
}

/**
 * Handles session expiration and redirects user to login
 */
export async function handleSessionExpired(): Promise<void> {
  try {
    // Sign out the user to clear all session data
    await authClient.signOut();

    // Redirect to login page
    if (typeof window !== 'undefined') {
      window.location.href = '/auth/login';
    }
  } catch {
    // Don't log sensitive error details that could expose internal information
    console.error('Error during session expiration handling');
    // Fallback redirect
    if (typeof window !== 'undefined') {
      window.location.href = '/auth/login';
    }
  }
}