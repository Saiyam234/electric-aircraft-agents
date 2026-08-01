import { NextResponse } from "next/server";
import { SESSION_COOKIE_NAME, credentialsMatch, sessionCookieValue } from "@/lib/session";

const DASHBOARD_USER = process.env.DASHBOARD_USER;
const DASHBOARD_PASSWORD = process.env.DASHBOARD_PASSWORD;

export async function POST(request: Request) {
  if (!DASHBOARD_USER || !DASHBOARD_PASSWORD) {
    return NextResponse.json({ error: "Auth is not configured on this deployment" }, { status: 500 });
  }

  const body = await request.json().catch(() => null);
  const username = typeof body?.username === "string" ? body.username : "";
  const password = typeof body?.password === "string" ? body.password : "";

  if (!credentialsMatch(username, password, DASHBOARD_USER, DASHBOARD_PASSWORD)) {
    return NextResponse.json({ error: "Incorrect username or password" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  // No maxAge: a browser-session cookie, not a persistent one. Sign-in is
  // the first thing you see every time you open the app in a new browser
  // session, rather than staying signed in for weeks.
  res.cookies.set(SESSION_COOKIE_NAME, sessionCookieValue(DASHBOARD_PASSWORD), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
  });
  return res;
}
