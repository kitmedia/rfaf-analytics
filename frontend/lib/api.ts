const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Error del servidor" }));
    throw new Error(error.detail || `Error ${res.status}`);
  }

  return res.json();
}

// --- Types ---

export interface AnalyzeRequest {
  youtube_url: string;
  equipo_local: string;
  equipo_visitante: string;
  competicion?: string;
  club_id: string;
}

export interface AnalyzeResponse {
  analysis_id: string;
  status: string;
  check_url: string;
}

export interface AnalysisStatus {
  analysis_id: string;
  status: string;
  progress_pct: number;
  current_step: string | null;
  estimated_remaining_seconds: number | null;
  xg_local: number | null;
  xg_visitante: number | null;
  contenido_md: string | null;
  pdf_url: string | null;
}

export interface ReportSummary {
  analysis_id: string;
  equipo_local: string;
  equipo_visitante: string;
  competicion: string | null;
  status: string;
  xg_local: number | null;
  xg_visitante: number | null;
  created_at: string;
}

export interface ReportDetail {
  analysis_id: string;
  equipo_local: string;
  equipo_visitante: string;
  competicion: string | null;
  status: string;
  xg_local: number | null;
  xg_visitante: number | null;
  contenido_md: string | null;
  charts_json: Record<string, string> | null;
  cost_gemini: number | null;
  cost_claude: number | null;
  duration_s: number | null;
  created_at: string;
}

export interface Club {
  id: string;
  name: string;
  email: string;
  plan: string;
  analisis_mes_actual: number;
  active: boolean;
  created_at: string;
}

// --- API Functions ---

export async function analyzeMatch(data: AnalyzeRequest): Promise<AnalyzeResponse> {
  return fetchAPI("/api/analyze/match", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
  return fetchAPI(`/api/analyze/status/${analysisId}`);
}

export async function listReports(clubId: string): Promise<ReportSummary[]> {
  return fetchAPI(`/api/reports?club_id=${clubId}`);
}

export async function getReport(analysisId: string): Promise<ReportDetail> {
  return fetchAPI(`/api/reports/${analysisId}`);
}

export async function getClub(clubId: string): Promise<Club> {
  return fetchAPI(`/api/clubs/${clubId}`);
}

export function getPdfUrl(analysisId: string): string {
  return `${API_BASE}/api/reports/${analysisId}/pdf`;
}
