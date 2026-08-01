import crypto from "node:crypto";

// A stateless session: the cookie's value is an HMAC of a fixed string
// keyed by DASHBOARD_PASSWORD, not a random token in a store. There's one
// shared credential for one owner, not per-user accounts, so there's
// nothing a session store would add — anyone who can reproduce the HMAC
// necessarily already knows the password.
export const SESSION_COOKIE_NAME = "ea_session";

function timingSafeEqual(a: string, b: string): boolean {
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

export function sessionCookieValue(password: string): string {
  return crypto.createHmac("sha256", password).update("electric-aircraft-session").digest("hex");
}

export function isValidSessionCookie(cookieValue: string | undefined, password: string): boolean {
  if (!cookieValue) return false;
  return timingSafeEqual(cookieValue, sessionCookieValue(password));
}

export function credentialsMatch(
  username: string,
  password: string,
  expectedUser: string,
  expectedPassword: string
): boolean {
  return timingSafeEqual(username, expectedUser) && timingSafeEqual(password, expectedPassword);
}
