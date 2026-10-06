/**
 * Authentication utilities for handling protected routes
 */

import { User } from '@/types';

export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') {
    return false; // Server-side rendering, assume not authenticated
  }

  const token = localStorage.getItem('auth_token');
  return !!token;
}

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return localStorage.getItem('auth_token');
}

export function clearAuthData(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    localStorage.removeItem('refresh_token');
  }
}

export function getUserData(): User | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const userData = localStorage.getItem('user');
  if (!userData) {
    return null;
  }

  try {
    return JSON.parse(userData) as User;
  } catch (error) {
    console.error('Failed to parse user data:', error);
    return null;
  }
}

export function setUserData(user: User): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('user', JSON.stringify(user));
  }
}