"use client";

import { useEffect, useState } from "react";
import { getFederationDashboard, type FederationDashboard } from "@/lib/api";

export default function FederationDashboardPage() {
  const [data, setData] = useState<FederationDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFederationDashboard()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          Error al cargar el dashboard federativo.
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard Federativo</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <MetricCard label="Clubes totales" value={data.total_clubs} />
        <MetricCard label="Clubes activos" value={data.active_clubs} />
        <MetricCard label="Analisis este mes" value={data.analyses_this_month} />
        <MetricCard label="Analisis totales" value={data.analyses_total} />
      </div>

      {data.avg_xg_local != null && data.avg_xg_visitante != null && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">xG Promedio (agregado)</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <p className="text-sm text-gray-500">Local</p>
              <p className="text-2xl font-bold text-indigo-600">{data.avg_xg_local.toFixed(2)}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">Visitante</p>
              <p className="text-2xl font-bold text-red-500">{data.avg_xg_visitante.toFixed(2)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-5 text-center">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
    </div>
  );
}
