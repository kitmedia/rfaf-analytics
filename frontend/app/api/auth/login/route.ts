import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const COOKIE_NAME = "rfaf_token";
const COOKIE_MAX_AGE = 24 * 60 * 60; // 24 hours in seconds

export async function POST(request: NextRequest) {
  const body = await request.json();

  const backendRes = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await backendRes.json();

  if (!backendRes.ok) {
    return NextResponse.json(data, { status: backendRes.status });
  }

  const response = NextResponse.json(data, { status: 200 });

  // Set httpOnly cookie — not accessible from JS, safe from XSS
  response.cookies.set(COOKIE_NAME, data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: COOKIE_MAX_AGE,
    path: "/",
  });

  // Store club metadata in a non-httpOnly cookie so client JS can read it
  response.cookies.set(
    "rfaf_meta",
    JSON.stringify({
      club_id: data.club_id,
      club_name: data.club_name,
      user_name: data.user_name,
      plan: data.plan,
    }),
    {
      httpOnly: false,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: COOKIE_MAX_AGE,
      path: "/",
    },
  );

  return response;
}
