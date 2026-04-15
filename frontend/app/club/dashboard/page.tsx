"use client";

import { useEffect, useState } from "react";
import { getClubId } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ClubDashboard {
  analyses_this_month: number;
  analyses_total: number;
  plan: string;
  plan_limit: number | null;
  usage_pct: number;
  last_analysis_date: string | null;
}

export default function ClubDashboardPage() {
  const [data, setData] = useState<ClubDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const clubId = getClubId() || "";

  useEffect(() => {
    if (!clubId) return;
    fetch(`${API_BASE}/api/clubs/${clubId}/dashboard`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [clubId]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (!data) {
    return <div className="p-8 text-gray-500">No se pudo cargar el dashboard.</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard del Club</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-xl shadow-sm border p-5 text-center">
          <p className="text-sm text-gray-500">Analisis este mes</p>
          <p className="text-3xl font-bold text-indigo-600 mt-1">{data.analyses_this_month}</p>
          {data.plan_limit && (
            <p className="text-xs text-gray-400 mt-1">de {data.plan_limit} disponibles</p>
          )}
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5 text-center">
          <p className="text-sm text-gray-500">Total historico</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{data.analyses_total}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5 text-center">
          <p className="text-sm text-gray-500">Plan</p>
          <p className="text-xl font-bold text-gray-900 mt-1 capitalize">{data.plan}</p>
        </div>
      </div>

      {data.plan_limit && (
        <div className="bg-white rounded-xl shadow-sm border p-5 mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-600">Uso del plan</span>
            <span className="font-medium">{data.usage_pct}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all ${data.usage_pct > 80 ? "bg-red-500" : "bg-indigo-600"}`}
              style={{ width: `${Math.min(data.usage_pct, 100)}%` }}
            />
          </div>
        </div>
      )}

      {data.last_analysis_date && (
        <p className="text-sm text-gray-500">
          Ultimo analisis: {new Date(data.last_analysis_date).toLocaleDateString("es-ES", { year: "numeric", month: "long", day: "numeric" })}
        </p>
      )}
    </div>
  );
}
