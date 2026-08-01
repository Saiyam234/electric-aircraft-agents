import { NextRequest, NextResponse } from "next/server";

// Same-origin relay to the real Flask API. The browser talks only to this
// app's own origin (already gated by proxy.ts's session cookie) — it never
// sees the backend's URL or its DASHBOARD_USER/PASSWORD, which live only
// here, server-side. Nothing here renders HTML; it just forwards method,
// path, query string, and body, and attaches the credential the backend's
// own before_request check expects.

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5001";
const DASHBOARD_USER = process.env.DASHBOARD_USER;
const DASHBOARD_PASSWORD = process.env.DASHBOARD_PASSWORD;

async function forward(request: NextRequest, path: string[]) {
  // `path` is everything after /backend/ — callers already pass paths like
  // /backend/api/overview (lib/api.ts's BASE_URL is "/backend", and its
  // call sites already say "/api/overview"), so path here is already
  // ["api", "overview"]. Don't add another "/api/" or requests double up
  // to /api/api/overview against the real backend.
  const url = new URL(`${BACKEND_URL}/${path.join("/")}`);
  url.search = request.nextUrl.search;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  if (DASHBOARD_USER && DASHBOARD_PASSWORD) {
    const encoded = Buffer.from(`${DASHBOARD_USER}:${DASHBOARD_PASSWORD}`).toString("base64");
    headers.set("authorization", `Basic ${encoded}`);
  }

  const init: RequestInit = { method: request.method, headers };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch {
    return NextResponse.json({ error: "Could not reach the backend API" }, { status: 502 });
  }

  const body = await upstream.text();
  return new NextResponse(body, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteContext) {
  return forward(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  return forward(request, (await params).path);
}
