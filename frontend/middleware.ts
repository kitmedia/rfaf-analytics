import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/signup", "/pricing", "/forgot-password", "/reset-password"];
const HOME_PATH = "/";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths, home (landing/dashboard hybrid), and static assets
  if (
    pathname === HOME_PATH ||
    PUBLIC_PATHS.some((p) => pathname.startsWith(p)) ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Check for auth token in cookie (set by client after login)
  const token = request.cookies.get("rfaf_token")?.value;

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
