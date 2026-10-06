import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Define protected routes that require authentication
const protectedRoutes = ['/dashboard', '/profile', '/settings', '/tasks'];

export function proxy(request: NextRequest) {
  // Check if the current route is protected
  const isProtectedRoute = protectedRoutes.some(route =>
    request.nextUrl.pathname.startsWith(route)
  );

  if (isProtectedRoute) {
    // Check if auth token exists in cookies or headers
    const authToken = request.cookies.get('auth_token')?.value ||
                      request.headers.get('authorization')?.replace('Bearer ', '') ||
                      request.headers.get('Authorization')?.replace('Bearer ', '');

    // For Next.js App Router, we need to check localStorage which is browser-only
    // So we'll rely on the client-side protection in ProtectedRoute component
    // For server-side, we'll check if there's a token in the request
    if (!authToken) {
      // No auth token found, redirect to login
      const url = request.nextUrl.clone();
      url.pathname = '/auth/login';
      url.searchParams.set('callbackUrl', request.nextUrl.pathname);
      return NextResponse.redirect(url);
    }
  }

  // Allow the request to proceed
  return NextResponse.next();
}

// Configure which routes the middleware should run on
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
