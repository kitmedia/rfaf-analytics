"use client";

import { useEffect, useState } from "react";
import { getAdminDashboard, type AdminDashboard } from "@/lib/api";

export default function AdminPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const d = await getAdminDashboard();
        setData(d);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar el panel");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || "No se pudo cargar el panel de administracion"}
        </div>
      </div>
    );
  }

  const planColors: Record<string, string> = {
    BASICO: "bg-gray-100 text-gray-800",
    PROFESIONAL: "bg-indigo-100 text-indigo-800",
    FEDERADO: "bg-amber-100 text-amber-800",
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900">Panel de administracion RFAF</h1>
      <p className="text-gray-500 text-sm mt-1">Metricas en tiempo real de la plataforma</p>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        <KpiCard label="MRR" value={`${data.mrr_eur.toFixed(0)} EUR`} sub="Ingresos mensuales" accent="text-green-600" />
        <KpiCard label="Margen" value={`${data.margin_pct.toFixed(1)}%`} sub="Ingresos - costes IA" accent="text-green-600" />
        <KpiCard label="Clubes activos" value={`${data.active_clubs}`} sub={`${data.total_clubs} total`} accent="text-indigo-600" />
        <KpiCard label="Analisis completados" value={`${data.analyses_done}`} sub={`${data.total_analyses} total`} accent="text-indigo-600" />
      </div>

      {/* Costs + Feedback row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Costes IA */}
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Costes IA</h2>
          <div className="space-y-3">
            <CostRow label="Gemini (video)" value={data.total_cost_gemini} />
            <CostRow label="Claude (informes)" value={data.total_cost_claude} />
            <div className="border-t pt-3">
              <CostRow label="Total" value={data.total_cost_eur} bold />
            </div>
          </div>
        </div>

        {/* Feedback */}
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Feedback</h2>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-indigo-600">
                {data.avg_rating !== null ? data.avg_rating.toFixed(1) : "-"}
              </p>
              <p className="text-xs text-gray-500 mt-1">Valoracion media</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-gray-700">{data.feedback_count}</p>
              <p className="text-xs text-gray-500 mt-1">Respuestas</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-red-500">{data.analyses_error}</p>
              <p className="text-xs text-gray-500 mt-1">Analisis con error</p>
            </div>
          </div>
        </div>
      </div>

      {/* Clubs by plan */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mt-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Clubes por plan</h2>
        <div className="flex gap-4">
          {Object.entries(data.clubs_by_plan).map(([plan, count]) => (
            <div
              key={plan}
              className={`px-4 py-3 rounded-lg ${planColors[plan] || "bg-gray-100 text-gray-800"}`}
            >
              <p className="text-2xl font-bold">{count}</p>
              <p className="text-xs font-medium mt-1">{plan}</p>
            </div>
          ))}
          {Object.keys(data.clubs_by_plan).length === 0 && (
            <p className="text-gray-400 text-sm">No hay clubes registrados</p>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  accent: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <p className="text-xs text-gray-500 font-medium">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${accent}`}>{value}</p>
      <p className="text-xs text-gray-400 mt-1">{sub}</p>
    </div>
  );
}

function CostRow({ label, value, bold }: { label: string; value: number; bold?: boolean }) {
  return (
    <div className="flex justify-between items-center">
      <span className={`text-sm ${bold ? "font-semibold text-gray-900" : "text-gray-600"}`}>
        {label}
      </span>
      <span className={`text-sm font-mono ${bold ? "font-bold text-gray-900" : "text-gray-700"}`}>
        {value.toFixed(4)} EUR
      </span>
    </div>
  );
}
