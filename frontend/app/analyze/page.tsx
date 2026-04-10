"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeMatch } from "@/lib/api";
import { trackEvent } from "@/lib/posthog";

const DEMO_CLUB_ID = "00000000-0000-0000-0000-000000000001";

export default function AnalyzePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    youtube_url: "",
    equipo_local: "",
    equipo_visitante: "",
    competicion: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await analyzeMatch({
        ...form,
        competicion: form.competicion || undefined,
        club_id: DEMO_CLUB_ID,
      });
      trackEvent("analysis_submitted", {
        equipo_local: form.equipo_local,
        equipo_visitante: form.equipo_visitante,
      });
      router.push(`/analyze/${result.analysis_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al encolar el análisis");
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Nuevo análisis de partido</h1>
      <p className="text-gray-500 mt-1">
        Introduce la URL de YouTube del partido y los equipos
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            URL de YouTube *
          </label>
          <input
            type="url"
            required
            placeholder="https://www.youtube.com/watch?v=..."
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
            value={form.youtube_url}
            onChange={(e) => setForm({ ...form, youtube_url: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Equipo local *
            </label>
            <input
              type="text"
              required
              placeholder="CD Ejea"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
              value={form.equipo_local}
              onChange={(e) => setForm({ ...form, equipo_local: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Equipo visitante *
            </label>
            <input
              type="text"
              required
              placeholder="SD Tarazona"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
              value={form.equipo_visitante}
              onChange={(e) => setForm({ ...form, equipo_visitante: e.target.value })}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Competición
          </label>
          <input
            type="text"
            placeholder="Tercera RFEF Grupo XVII"
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
            value={form.competicion}
            onChange={(e) => setForm({ ...form, competicion: e.target.value })}
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Encolando análisis..." : "🚀 Analizar partido"}
        </button>
      </form>
    </div>
  );
}
