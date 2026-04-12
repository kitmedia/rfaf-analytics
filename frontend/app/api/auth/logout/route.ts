import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.delete("rfaf_token");
  response.cookies.delete("rfaf_meta");
  return response;
}
