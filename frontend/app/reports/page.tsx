"use client";

import { useEffect, useState } from "react";
import { listReports, type ReportSummary } from "@/lib/api";

const DEMO_CLUB_ID = "00000000-0000-0000-0000-000000000001";

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listReports(DEMO_CLUB_ID)
      .then(setReports)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Informes</h1>
        <a
          href="/analyze"
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
        >
          + Nuevo análisis
        </a>
      </div>

      {reports.length === 0 ? (
        <div className="mt-8 bg-white rounded-xl shadow-sm border p-12 text-center">
          <p className="text-gray-500">No hay informes todavía.</p>
          <a href="/analyze" className="text-indigo-600 hover:text-indigo-800 text-sm font-medium mt-2 inline-block">
            Analiza tu primer partido →
          </a>
        </div>
      ) : (
        <div className="mt-6 grid gap-4">
          {reports.map((r) => (
            <a
              key={r.analysis_id}
              href={r.status === "done" ? `/reports/${r.analysis_id}` : `/analyze/${r.analysis_id}`}
              className="bg-white rounded-xl shadow-sm border p-5 hover:shadow-md transition-shadow flex items-center justify-between"
            >
              <div>
                <p className="font-medium text-gray-900">
                  {r.equipo_local} vs {r.equipo_visitante}
                </p>
                {r.competicion && (
                  <p className="text-sm text-gray-400">{r.competicion}</p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(r.created_at).toLocaleDateString("es-ES")}
                </p>
              </div>
              <div className="flex items-center gap-4">
                {r.xg_local != null && r.xg_visitante != null && (
                  <span className="text-sm font-medium text-gray-600">
                    xG: {r.xg_local.toFixed(2)} - {r.xg_visitante.toFixed(2)}
                  </span>
                )}
                <StatusBadge status={r.status} />
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    done: "bg-green-100 text-green-700",
    processing: "bg-amber-100 text-amber-700",
    pending: "bg-blue-100 text-blue-700",
    error: "bg-red-100 text-red-700",
  };
  const labels: Record<string, string> = {
    done: "Completado",
    processing: "Procesando",
    pending: "En cola",
    error: "Error",
  };

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || "bg-gray-100 text-gray-700"}`}>
      {labels[status] || status}
    </span>
  );
}
