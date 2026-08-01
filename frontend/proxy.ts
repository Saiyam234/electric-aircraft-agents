import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE_NAME, isValidSessionCookie } from "@/lib/session";

// Gates every page and API route behind a real login screen (not a browser
// Basic Auth popup) — this is a solo-owner tool, not a multi-user product,
// so one shared password is enough. Unset locally on purpose (localhost is
// already private); must be set on Railway/prod or the dashboard is public
// to anyone with the link.
const DASHBOARD_PASSWORD = process.env.DASHBOARD_PASSWORD;

const PUBLIC_PATHS = ["/login", "/api/login", "/_next", "/favicon.ico"];

export function proxy(request: NextRequest) {
  if (!DASHBOARD_PASSWORD) return NextResponse.next();

  const { pathname } = request.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return NextResponse.next();
  }

  const cookie = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (isValidSessionCookie(cookie, DASHBOARD_PASSWORD)) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/backend/")) {
    return NextResponse.json({ error: "Authentication required" }, { status: 401 });
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}
