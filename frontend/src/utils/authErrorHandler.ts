/**
 * Authentication error handler with proper error categorization
 */

import { isAxiosError } from 'axios';

export class AuthError extends Error {
  public readonly status: number;
  public readonly code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = 'AuthError';
    this.status = status;
    this.code = code;
  }
}

export enum AuthErrorCode {
  SESSION_EXPIRED = 'SESSION_EXPIRED',
  UNAUTHORIZED = 'UNAUTHORIZED',
  TOKEN_INVALID = 'TOKEN_INVALID',
  NETWORK_ERROR = 'NETWORK_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
}

/**
 * Handles authentication errors based on the error type
 * @param error The error to handle
 * @returns A categorized AuthError
 */
export function handleAuthError(error: unknown): AuthError {
  // Check if it's already an AuthError
  if (error instanceof AuthError) {
    return error;
  }

  // Check if it's an Axios error
  if (isAxiosError(error)) {
    const status = error.response?.status ?? 0;

    switch (status) {
      case 401:
        return new AuthError(
          'Unauthorized access. Please log in again.',
          status,
          AuthErrorCode.UNAUTHORIZED
        );

      case 403:
        return new AuthError(
          'Access forbidden. Please contact your administrator.',
          status,
          AuthErrorCode.UNAUTHORIZED
        );

      case 422:
        return new AuthError(
          'Validation error occurred.',
          status,
          AuthErrorCode.VALIDATION_ERROR
        );

      case 500:
      case 502:
      case 503:
        return new AuthError(
          'Server error occurred. Please try again later.',
          status,
          AuthErrorCode.SERVER_ERROR
        );

      default:
        if (error.code === 'NETWORK_ERROR' || !error.response) {
          return new AuthError(
            'Network error occurred. Please check your connection.',
            0,
            AuthErrorCode.NETWORK_ERROR
          );
        }
        // Prevent information disclosure by not exposing internal error details
        const detail = error.response?.data?.detail;
        const errorMessage = status >= 500
          ? 'Server error occurred. Please try again later.'
          : typeof detail === 'string' ? detail : 'An error occurred during authentication.';

        return new AuthError(
          errorMessage,
          status || 500,
          AuthErrorCode.SERVER_ERROR
        );
    }
  }

  // For non-Axios errors
  return new AuthError(
    error instanceof Error && error.message ? error.message : 'An unknown error occurred',
    500,
    AuthErrorCode.SERVER_ERROR
  );
}

/**
 * Logs authentication errors for debugging purposes
 * @param error The error to log
 */
export function logAuthError(error: AuthError): void {
  // Log only non-sensitive error information to prevent information disclosure
  console.error('Authentication Error:', {
    status: error.status,
    code: error.code,
    timestamp: new Date().toISOString(),
    // Only log the general message, not detailed internal errors
    message: error.message,
  });
}

/**
 * Handles specific authentication error codes
 * @param errorCode The error code to handle
 */
export function handleSpecificAuthError(errorCode: AuthErrorCode): void {
  switch (errorCode) {
    case AuthErrorCode.SESSION_EXPIRED:
    case AuthErrorCode.UNAUTHORIZED:
      // Redirect to login page
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
      break;

    case AuthErrorCode.TOKEN_INVALID:
      // Clear invalid token and redirect to login
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
        window.location.href = '/auth/login';
      }
      break;

    case AuthErrorCode.NETWORK_ERROR:
      console.warn('Network error occurred. Please check your connection.');
      break;

    case AuthErrorCode.SERVER_ERROR:
      console.error('Server error occurred. Please try again later.');
      break;

    case AuthErrorCode.VALIDATION_ERROR:
      console.warn('Validation error occurred. Please check your input.');
      break;
  }
}