/**
 * Shared client-side session helpers: JWT expiry checks and a single
 * "session is over" teardown used by every auth path (axios interceptor,
 * raw fetch/XHR in chat, AuthContext watchdog).
 */

const AUTH_KEYS = ['auth_token', 'user', 'refresh_token'] as const;

/** Decode a JWT payload without verifying it (server remains authoritative). */
export function parseJwtExp(token: string): number | null {
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const base64 = part.replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(json) as { exp?: unknown };
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/**
 * True when the access token is expired (or within `skewMs` of expiring).
 * Tokens with no decodable exp are treated as valid — the server's 401
 * remains the source of truth for those.
 */
export function isTokenExpired(token: string | null, skewMs = 5000): boolean {
  if (!token) return true;
  const exp = parseJwtExp(token);
  if (exp === null) return false;
  return Date.now() >= exp - skewMs;
}

/** Remove every auth artifact from localStorage and the middleware cookie. */
export function clearAuthStorage(): void {
  if (typeof window === 'undefined') return;
  for (const key of AUTH_KEYS) localStorage.removeItem(key);
  document.cookie =
    'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
}

/** Persist the middleware cookie for a token, lifetime aligned to its exp. */
export function setAuthCookie(token: string): void {
  if (typeof window === 'undefined') return;
  const exp = parseJwtExp(token);
  const maxAge = exp
    ? Math.max(60, Math.floor((exp - Date.now()) / 1000))
    : 60 * 60 * 24 * 7;
  document.cookie = `auth_token=${token}; path=/; max-age=${maxAge}; SameSite=Lax`;
}

/**
 * Full session teardown + hard navigation to the sign-in page.
 * Hard navigation guarantees no stale UI (chat retry banners, stuck cards)
 * survives the logout. No-ops on the login/register pages to avoid loops.
 */
export function redirectToLogin(): void {
  if (typeof window === 'undefined') return;
  clearAuthStorage();
  const path = window.location.pathname;
  if (path.startsWith('/auth/login') || path.startsWith('/auth/register')) {
    return;
  }
  window.location.href = '/auth/login';
}

/** Thrown when an API response comes back 401 (session expired/invalid). */
export class AuthSessionExpiredError extends Error {
  constructor(message = 'Session expired') {
    super(message);
    this.name = 'AuthSessionExpiredError';
  }
}

/**
 * Guard for fetch responses: throws AuthSessionExpiredError on 401 so
 * callers can skip generic error UI and redirect instead.
 */
export function ensureAuthorized(response: Response): void {
  if (response.status === 401) {
    throw new AuthSessionExpiredError();
  }
}
