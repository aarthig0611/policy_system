/**
 * Next.js Proxy (formerly Middleware) — protect all routes under the (app) group.
 *
 * If the `token` cookie is absent the user is redirected to /login.
 * Public routes: /login, /api/*, /_next/*, /favicon.ico
 *
 * Note: In Next.js 16 the file convention was renamed from middleware.ts to
 * proxy.ts and the export from `middleware` to `proxy`.
 */

import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/api/"];

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname.startsWith(p));
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always allow static files and Next.js internals
  if (pathname.startsWith("/_next/") || pathname === "/favicon.ico") {
    return NextResponse.next();
  }

  const token = request.cookies.get("token");

  // Inject Authorization header for backend proxy requests so FastAPI's
  // HTTPBearer dependency can read it (the token lives in an httpOnly cookie,
  // not the Authorization header, so we bridge them here).
  if (pathname.startsWith("/api/backend/")) {
    if (!token) {
      return NextResponse.next(); // FastAPI will return 401
    }
    const headers = new Headers(request.headers);
    headers.set("Authorization", `Bearer ${token.value}`);
    return NextResponse.next({ request: { headers } });
  }

  // Public page routes pass through without a token check
  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  // All other routes require the token cookie
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    // Preserve the originally requested path so we can redirect after login
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// Apply to all routes except Next.js internals and static assets
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
