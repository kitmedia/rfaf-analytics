"use client";

import { useEffect, useState, useCallback } from "react";
import { listAdminAnalyses, retryAnalysis, type AdminAnalysisItem } from "@/lib/api";

const statusTabs = [
  { key: "", label: "Todos" },
  { key: "pending", label: "Pendientes" },
  { key: "processing", label: "En proceso" },
  { key: "done", label: "Completados" },
  { key: "error", label: "Error" },
];

const statusColors: Record<string, string> = {
  done: "bg-green-100 text-green-800",
  processing: "bg-amber-100 text-amber-800",
  pending: "bg-blue-100 text-blue-800",
  error: "bg-red-100 text-red-800",
};

export default function AdminAnalysesPage() {
  const [analyses, setAnalyses] = useState<AdminAnalysisItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listAdminAnalyses(statusFilter || undefined, undefined, page);
      setAnalyses(data.analyses);
      setTotal(data.total);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar analisis");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleRetry(analysisId: string) {
    try {
      setRetrying(analysisId);
      await retryAnalysis(analysisId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al reintentar");
    } finally {
      setRetrying(null);
    }
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Analisis</h1>
        <p className="text-gray-500 text-sm mt-1">{total} analisis en total</p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 mb-6">
        {statusTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              setStatusFilter(tab.key);
              setPage(1);
            }}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              statusFilter === tab.key
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Equipos</th>
                <th className="px-4 py-3 font-medium">Club</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="px-4 py-3 font-medium">Progreso</th>
                <th className="px-4 py-3 font-medium">Coste</th>
                <th className="px-4 py-3 font-medium">Duracion</th>
                <th className="px-4 py-3 font-medium">Creado</th>
                <th className="px-4 py-3 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {analyses.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {a.equipo_local} vs {a.equipo_visitante}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{a.club_name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${statusColors[a.status] || "bg-gray-100 text-gray-800"}`}
                    >
                      {a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-indigo-600 h-1.5 rounded-full"
                          style={{ width: `${a.progress_pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">{a.progress_pct}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs font-mono">
                    {a.cost_gemini != null || a.cost_claude != null
                      ? `${((a.cost_gemini || 0) + (a.cost_claude || 0)).toFixed(4)} EUR`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {a.duration_s != null ? `${a.duration_s.toFixed(0)}s` : "-"}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {new Date(a.created_at).toLocaleDateString("es-ES")}
                  </td>
                  <td className="px-4 py-3">
                    {a.status === "error" && (
                      <button
                        onClick={() => handleRetry(a.id)}
                        disabled={retrying === a.id}
                        className="text-indigo-600 hover:text-indigo-800 text-xs font-medium disabled:opacity-50"
                      >
                        {retrying === a.id ? "Reintentando..." : "Reintentar"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {analyses.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                    No hay analisis
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-40 hover:bg-gray-50"
          >
            Anterior
          </button>
          <span className="px-3 py-1.5 text-sm text-gray-500">Pagina {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={analyses.length < 20}
            className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-40 hover:bg-gray-50"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
}
