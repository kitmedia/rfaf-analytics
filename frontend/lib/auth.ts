const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AuthData {
  access_token: string;
  club_id: string;
  club_name: string;
  user_name: string;
  role: string;
  plan: string;
  expires_in: number;
}

export async function login(email: string, password: string): Promise<AuthData> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Error de autenticación");
  }

  const data: AuthData = await res.json();
  saveAuth(data);
  return data;
}

export async function register(
  clubName: string,
  name: string,
  email: string,
  password: string,
): Promise<AuthData> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ club_name: clubName, name, email, password }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Error al registrarse");
  }

  const data: AuthData = await res.json();
  saveAuth(data);
  return data;
}

export function saveAuth(data: AuthData) {
  if (typeof window === "undefined") return;
  localStorage.setItem("rfaf_auth", JSON.stringify(data));
  // Set cookie for Next.js middleware (middleware can't read localStorage)
  document.cookie = `rfaf_token=${data.access_token}; path=/; max-age=${data.expires_in}; SameSite=Lax`;
}

export function getAuth(): AuthData | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("rfaf_auth");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return getAuth()?.access_token ?? null;
}

export function getClubId(): string | null {
  return getAuth()?.club_id ?? null;
}

export function logout() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("rfaf_auth");
  document.cookie = "rfaf_token=; path=/; max-age=0";
  window.location.href = "/login";
}

export function isAuthenticated(): boolean {
  return getAuth() !== null;
}
