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

export interface AdminDashboard {
  total_clubs: number;
  active_clubs: number;
  mrr_eur: number;
  total_analyses: number;
  analyses_done: number;
  analyses_error: number;
  total_cost_gemini: number;
  total_cost_claude: number;
  total_cost_eur: number;
  margin_pct: number;
  avg_rating: number | null;
  feedback_count: number;
  clubs_by_plan: Record<string, number>;
}

export async function getAdminDashboard(): Promise<AdminDashboard> {
  return fetchAdminAPI("/api/admin/dashboard");
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
  token: string,
): Promise<{ message: string }> {
  return fetchAPI("/api/auth/change-password", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export interface ChatResponse {
  answer: string;
  model: string;
}

export async function chatAboutReport(
  analysisId: string,
  question: string,
  clubId: string,
): Promise<ChatResponse> {
  return fetchAPI(`/api/reports/${analysisId}/chat`, {
    method: "POST",
    body: JSON.stringify({ question, club_id: clubId }),
  });
}

// ─── Admin API ───────────────────────────────────────────────────────────────

async function fetchAdminAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const { getToken } = await import("@/lib/auth");
  const token = getToken();
  return fetchAPI(path, {
    ...options,
    headers: { ...options?.headers, Authorization: `Bearer ${token}` },
  });
}

// --- Admin Types ---

export interface AdminClubItem {
  id: string;
  name: string;
  email: string;
  plan: string;
  active: boolean;
  user_count: number;
  analysis_count: number;
  analisis_mes_actual: number;
  created_at: string;
}

export interface AdminUserItem {
  id: string;
  club_id: string;
  club_name: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
}

export interface AdminAnalysisItem {
  id: string;
  club_id: string;
  club_name: string;
  equipo_local: string;
  equipo_visitante: string;
  status: string;
  progress_pct: number;
  current_step: string | null;
  cost_gemini: number | null;
  cost_claude: number | null;
  duration_s: number | null;
  created_at: string;
}

export interface AdminFeedbackItem {
  id: string;
  club_id: string;
  club_name: string;
  category: string;
  rating: number;
  comment: string;
  created_at: string;
}

export interface CeleryTaskInfo {
  id: string;
  name: string;
  args: string;
  worker: string;
}

export interface BackupInfo {
  key: string;
  size_bytes: number;
  last_modified: string;
}

export interface MlModelStatus {
  exists: boolean;
  path: string;
  size_bytes: number | null;
  last_modified: string | null;
  metrics?: { brier_score: number; auc: number } | null;
}

// --- Admin Functions ---

export async function listAdminClubs(): Promise<{ clubs: AdminClubItem[]; total: number }> {
  const data = await fetchAdminAPI<{ items: AdminClubItem[]; total: number }>("/api/admin/clubs");
  return { clubs: data.items, total: data.total };
}

export async function onboardClub(data: {
  club_name: string;
  email: string;
  plan: string;
  admin_name: string;
  admin_password: string;
}): Promise<AdminClubItem> {
  return fetchAdminAPI("/api/admin/clubs", {
    method: "POST",
    body: JSON.stringify({
      club_name: data.club_name,
      club_email: data.email,
      plan: data.plan,
      admin_name: data.admin_name,
      admin_email: data.email,
      admin_password: data.admin_password,
    }),
  });
}

export async function updateClub(
  clubId: string,
  data: Partial<{ name: string; email: string; plan: string }>,
): Promise<AdminClubItem> {
  return fetchAdminAPI(`/api/admin/clubs/${clubId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function toggleClub(clubId: string): Promise<{ active: boolean }> {
  const result = await fetchAdminAPI<AdminClubItem>(
    `/api/admin/clubs/${clubId}/toggle`,
    { method: "PATCH" },
  );
  return { active: result.active };
}

export async function listAdminUsers(
  clubId?: string,
): Promise<{ users: AdminUserItem[]; total: number }> {
  const qs = clubId ? `?club_id=${clubId}` : "";
  const data = await fetchAdminAPI<{ items: AdminUserItem[]; total: number }>(`/api/admin/users${qs}`);
  return { users: data.items, total: data.total };
}

export async function createAdminUser(data: {
  club_id: string;
  name: string;
  email: string;
  password: string;
  role: string;
}): Promise<AdminUserItem> {
  return fetchAdminAPI("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateAdminUser(
  userId: string,
  data: Partial<{ name: string; email: string; role: string }>,
): Promise<AdminUserItem> {
  return fetchAdminAPI(`/api/admin/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function resetAdminUserPassword(
  userId: string,
): Promise<{ temporary_password: string }> {
  const data = await fetchAdminAPI<{ user_id: string; temp_password: string; message: string }>(
    `/api/admin/users/${userId}/reset-password`,
    { method: "POST" },
  );
  return { temporary_password: data.temp_password };
}

export async function listAdminAnalyses(
  status?: string,
  clubId?: string,
  page?: number,
): Promise<{ analyses: AdminAnalysisItem[]; total: number; page: number }> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (clubId) params.set("club_id", clubId);
  if (page) params.set("page", String(page));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const data = await fetchAdminAPI<{ items: AdminAnalysisItem[]; total: number; page: number }>(
    `/api/admin/analyses${qs}`,
  );
  return { analyses: data.items, total: data.total, page: data.page };
}

export async function retryAnalysis(analysisId: string): Promise<{ task_id: string }> {
  return fetchAdminAPI(`/api/admin/analyses/${analysisId}/retry`, { method: "POST" });
}

export async function listCeleryTasks(): Promise<{
  active: CeleryTaskInfo[];
  reserved: CeleryTaskInfo[];
  scheduled: CeleryTaskInfo[];
}> {
  // Backend returns raw Celery inspect dicts { worker_name: [...tasks] }
  // Flatten into arrays for the frontend
  const data = await fetchAdminAPI<{
    active: Record<string, CeleryTaskInfo[]>;
    reserved: Record<string, CeleryTaskInfo[]>;
    scheduled: Record<string, CeleryTaskInfo[]>;
  }>("/api/admin/tasks");
  return {
    active: Object.values(data.active).flat(),
    reserved: Object.values(data.reserved).flat(),
    scheduled: Object.values(data.scheduled).flat(),
  };
}

export async function getCeleryTask(
  taskId: string,
): Promise<{ id: string; status: string; result: unknown }> {
  const data = await fetchAdminAPI<{ task_id: string; status: string; result: string | null; traceback: string | null }>(
    `/api/admin/tasks/${taskId}`,
  );
  return { id: data.task_id, status: data.status, result: data.result };
}

export async function triggerBackup(): Promise<{ task_id: string }> {
  return fetchAdminAPI("/api/admin/backups/trigger", { method: "POST" });
}

export async function listBackups(): Promise<BackupInfo[]> {
  const data = await fetchAdminAPI<{ items: BackupInfo[]; total: number }>("/api/admin/backups");
  return data.items;
}

export async function triggerXgTraining(): Promise<{ task_id: string }> {
  return fetchAdminAPI("/api/admin/ml/train-xg", { method: "POST" });
}

export async function getXgModelStatus(): Promise<MlModelStatus> {
  return fetchAdminAPI("/api/admin/ml/status");
}

export async function listAdminFeedbacks(
  clubId?: string,
  category?: string,
): Promise<{ feedbacks: AdminFeedbackItem[]; total: number }> {
  const params = new URLSearchParams();
  if (clubId) params.set("club_id", clubId);
  if (category) params.set("category", category);
  const qs = params.toString() ? `?${params.toString()}` : "";
  const data = await fetchAdminAPI<{ items: AdminFeedbackItem[]; total: number }>(
    `/api/admin/feedbacks${qs}`,
  );
  return { feedbacks: data.items, total: data.total };
}
