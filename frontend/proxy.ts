import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Gates every request (including static assets — deliberately no matcher)
// behind one shared password, since this is a solo-owner tool, not a
// multi-user product. Unset locally on purpose (localhost is already
// private); must be set on Railway/prod or the dashboard is public to
// anyone with the link.
const USER = process.env.DASHBOARD_USER;
const PASSWORD = process.env.DASHBOARD_PASSWORD;

function unauthorized() {
  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Electric Aircraft"' },
  });
}

export function proxy(request: NextRequest) {
  if (!USER || !PASSWORD) return NextResponse.next();

  const auth = request.headers.get("authorization");
  if (!auth?.startsWith("Basic ")) return unauthorized();

  const decoded = atob(auth.slice("Basic ".length));
  const separator = decoded.indexOf(":");
  if (separator === -1) return unauthorized();

  const user = decoded.slice(0, separator);
  const password = decoded.slice(separator + 1);
  if (user !== USER || password !== PASSWORD) return unauthorized();

  return NextResponse.next();
}
