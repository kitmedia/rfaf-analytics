"use client";

import { useEffect, useState } from "react";
import { listReports, getClub, type ReportSummary, type Club } from "@/lib/api";

// Default club for demo — replace with auth
const DEMO_CLUB_ID = "00000000-0000-0000-0000-000000000001";

export default function Dashboard() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [club, setClub] = useState<Club | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [r, c] = await Promise.all([
          listReports(DEMO_CLUB_ID),
          getClub(DEMO_CLUB_ID),
        ]);
        setReports(r);
        setClub(c);
      } catch {
        // Club might not exist yet
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const done = reports.filter((r) => r.status === "done").length;
  const processing = reports.filter((r) => r.status === "processing" || r.status === "pending").length;

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      {club && (
        <p className="text-gray-500 mt-1">
          {club.name} · Plan {club.plan} · {club.analisis_mes_actual} análisis este mes
        </p>
      )}

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <p className="text-sm text-gray-500">Informes completados</p>
          <p className="text-3xl font-bold text-indigo-600 mt-2">{done}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <p className="text-sm text-gray-500">En proceso</p>
          <p className="text-3xl font-bold text-amber-500 mt-2">{processing}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <p className="text-sm text-gray-500">Total análisis</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{reports.length}</p>
        </div>
      </div>

      {/* Quick actions */}
      <div className="mt-8">
        <a
          href="/analyze"
          className="inline-flex items-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
        >
          🎬 Nuevo análisis de partido
        </a>
      </div>

      {/* Recent reports */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Informes recientes</h2>
        {reports.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-500">
            No hay informes todavía. ¡Analiza tu primer partido!
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                    Partido
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                    Estado
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                    xG
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase">
                    Fecha
                  </th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {reports.map((r) => (
                  <tr key={r.analysis_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {r.equipo_local} vs {r.equipo_visitante}
                      {r.competicion && (
                        <span className="block text-xs text-gray-400">{r.competicion}</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {r.xg_local != null && r.xg_visitante != null
                        ? `${r.xg_local.toFixed(2)} - ${r.xg_visitante.toFixed(2)}`
                        : "—"}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(r.created_at).toLocaleDateString("es-ES")}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {r.status === "done" ? (
                        <a
                          href={`/reports/${r.analysis_id}`}
                          className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                        >
                          Ver informe →
                        </a>
                      ) : r.status === "pending" || r.status === "processing" ? (
                        <a
                          href={`/analyze/${r.analysis_id}`}
                          className="text-amber-600 hover:text-amber-800 text-sm font-medium"
                        >
                          Ver progreso →
                        </a>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
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
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        styles[status] || "bg-gray-100 text-gray-700"
      }`}
    >
      {labels[status] || status}
    </span>
  );
}
