"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getAnalysisStatus, type AnalysisStatus } from "@/lib/api";
import { trackEvent } from "@/lib/posthog";

export default function AnalysisProgressPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [error, setError] = useState("");
  const pollCount = useRef(0);
  const MAX_POLLS = 200; // ~10 min at 3s interval

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    async function poll() {
      pollCount.current += 1;

      if (pollCount.current > MAX_POLLS) {
        setError("El análisis está tardando demasiado. Consulta más tarde.");
        clearInterval(interval);
        return;
      }

      try {
        const data = await getAnalysisStatus(id);
        setStatus(data);

        if (data.status === "done") {
          clearInterval(interval);
          trackEvent("analysis_done_viewed", { analysis_id: id });
          setTimeout(() => router.push(`/reports/${id}`), 1500);
        } else if (data.status === "error") {
          clearInterval(interval);
          trackEvent("analysis_error_viewed", { analysis_id: id });
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al consultar estado");
        clearInterval(interval);
      }
    }

    poll();
    interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, [id, router]);

  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900">Análisis en curso</h1>

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {status && (
        <div className="mt-8 bg-white rounded-xl shadow-sm border p-8">
          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">{status.current_step || "Iniciando..."}</span>
              <span className="font-medium text-indigo-600">{status.progress_pct}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all duration-500 ${
                  status.status === "error" ? "bg-red-500" : "bg-indigo-600"
                }`}
                style={{ width: `${status.progress_pct}%` }}
              />
            </div>
          </div>

          {/* Status */}
          <div className="text-center">
            {status.status === "done" && (
              <div>
                <p className="text-green-600 font-semibold text-lg">
                  ✅ Informe completado
                </p>
                <p className="text-gray-500 text-sm mt-2">Redirigiendo al informe...</p>
              </div>
            )}
            {status.status === "error" && (
              <div>
                <p className="text-red-600 font-semibold text-lg">Error en el análisis</p>
                <p className="text-gray-500 text-sm mt-2">{status.current_step}</p>
                <a
                  href="/analyze"
                  className="inline-block mt-4 text-indigo-600 hover:text-indigo-800 font-medium text-sm"
                >
                  ← Intentar de nuevo
                </a>
              </div>
            )}
            {(status.status === "pending" || status.status === "processing") && (
              <div className="flex items-center justify-center gap-3 text-gray-500">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600" />
                <span>Procesando...</span>
              </div>
            )}
          </div>

          <p className="text-xs text-gray-400 text-center mt-6">
            ID: {status.analysis_id}
          </p>
        </div>
      )}
    </div>
  );
}
