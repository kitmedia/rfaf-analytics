/**
 * Auth helpers — token stored in httpOnly cookie (set by /api/auth/login server route).
 * Club metadata stored in rfaf_meta cookie (readable by JS).
 */

export interface AuthMeta {
  club_id: string;
  club_name: string;
  user_name: string;
  plan: string;
}

export interface AuthData extends AuthMeta {
  access_token: string;
  token_type: string;
  expires_in: number;
}

function _getMeta(): AuthMeta | null {
  if (typeof document === "undefined") return null;
  const raw = document.cookie
    .split("; ")
    .find((c) => c.startsWith("rfaf_meta="))
    ?.split("=")
    .slice(1)
    .join("=");
  if (!raw) return null;
  try {
    return JSON.parse(decodeURIComponent(raw));
  } catch {
    return null;
  }
}

export async function login(email: string, password: string): Promise<AuthData> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Error de autenticación");
  }

  return res.json();
}

export function getClubId(): string | null {
  return _getMeta()?.club_id ?? null;
}

export function getClubName(): string | null {
  return _getMeta()?.club_name ?? null;
}

export function getUserName(): string | null {
  return _getMeta()?.user_name ?? null;
}

export function getPlan(): string | null {
  return _getMeta()?.plan ?? null;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
}

export function isAuthenticated(): boolean {
  return _getMeta() !== null;
}
