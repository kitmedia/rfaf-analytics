"use client";

import { useEffect, useState, useCallback } from "react";
import { getAdminDashboard, type AdminDashboard } from "@/lib/api";

function StatCard({
  label,
  value,
  sub,
  color = "indigo",
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    indigo: "text-indigo-600",
    green: "text-green-600",
    red: "text-red-600",
    amber: "text-amber-600",
  };
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${colorMap[color] || "text-gray-900"}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function AdminDashboardPage() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const d = await getAdminDashboard();
      setData(d);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const totalCost = data.total_cost_eur;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard administracion</h1>

      {/* KPIs row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="MRR"
          value={`${data.mrr_eur.toFixed(0)} EUR`}
          color="green"
        />
        <StatCard
          label="Margen"
          value={`${data.margin_pct.toFixed(1)}%`}
          sub={`Coste IA: ${totalCost.toFixed(2)} EUR`}
          color={data.margin_pct > 80 ? "green" : "amber"}
        />
        <StatCard
          label="Clubes activos"
          value={`${data.active_clubs} / ${data.total_clubs}`}
        />
        <StatCard
          label="Valoracion media"
          value={data.avg_rating ? `${data.avg_rating} / 5` : "Sin datos"}
          sub={data.feedback_count > 0 ? `${data.feedback_count} respuestas` : undefined}
          color="amber"
        />
      </div>

      {/* Analysis stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total analisis" value={data.total_analyses} />
        <StatCard
          label="Completados"
          value={data.analyses_done}
          color="green"
        />
        <StatCard
          label="Con error"
          value={data.analyses_error}
          color={data.analyses_error > 0 ? "red" : "green"}
        />
        <StatCard
          label="Coste Gemini / Claude"
          value={`${data.total_cost_gemini.toFixed(2)} / ${data.total_cost_claude.toFixed(2)}`}
          sub="EUR"
        />
      </div>

      {/* Clubs by plan */}
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Clubes por plan</h2>
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(data.clubs_by_plan).map(([plan, count]) => {
            const colors: Record<string, string> = {
              basico: "bg-gray-100 text-gray-800",
              profesional: "bg-indigo-100 text-indigo-800",
              federado: "bg-amber-100 text-amber-800",
            };
            return (
              <div key={plan} className="text-center">
                <span
                  className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${colors[plan] || "bg-gray-100 text-gray-800"}`}
                >
                  {plan.toUpperCase()}
                </span>
                <p className="text-2xl font-bold mt-2">{count}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
