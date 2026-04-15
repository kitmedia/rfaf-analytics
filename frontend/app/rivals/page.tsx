"use client";

import { useState } from "react";
import Link from "next/link";
import { searchTeams, getTeamAnalyses, createManualUpcoming, type TeamSearchResult, type TeamAnalysesResponse } from "@/lib/api";
import { getClubId } from "@/lib/auth";
import { trackEvent } from "@/lib/posthog";

export default function RivalsPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TeamSearchResult[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<TeamAnalysesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const clubId = getClubId() || "";

  async function handleSearch(q: string) {
    setQuery(q);
    setSelectedTeam(null);
    setSaved(false);
    if (q.length < 2) {
      setResults([]);
      return;
    }
    try {
      const teams = await searchTeams(q);
      setResults(teams);
    } catch {
      setResults([]);
    }
  }

  async function handleSelectTeam(name: string) {
    setLoading(true);
    try {
      const data = await getTeamAnalyses(name);
      setSelectedTeam(data);
      setResults([]);
      setQuery(name);
      trackEvent("rival_searched", { rival: name, has_data: data.analysis_count > 0 });
    } catch {
      setSelectedTeam(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkAsRival() {
    if (!selectedTeam || !clubId) return;
    const nextWeek = new Date();
    nextWeek.setDate(nextWeek.getDate() + 7);
    try {
      await createManualUpcoming(clubId, selectedTeam.team_name, nextWeek.toISOString());
      setSaved(true);
      trackEvent("rival_marked", { rival: selectedTeam.team_name });
    } catch { /* silent */ }
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Buscar rival</h1>
      <p className="text-gray-500 mb-6">
        Busca tu proximo rival para ver si tenemos analisis disponibles.
      </p>

      {/* Search */}
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Escribe el nombre del equipo rival..."
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
        />

        {/* Autocomplete dropdown */}
        {results.length > 0 && (
          <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {results.map((team) => (
              <button
                key={team.name}
                onClick={() => handleSelectTeam(team.name)}
                className="w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0"
              >
                <span className="font-medium text-gray-900">{team.name}</span>
                <span className="text-gray-400 text-xs ml-2">({team.match_count} partidos)</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="mt-6 text-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto" />
        </div>
      )}

      {/* Selected team result */}
      {selectedTeam && !loading && (
        <div className="mt-6 bg-white rounded-xl shadow-sm border p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">{selectedTeam.team_name}</h2>

          {selectedTeam.analysis_count > 0 ? (
            <>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                <p className="text-green-800 font-medium">
                  Tenemos {selectedTeam.analysis_count} analisis de {selectedTeam.team_name}
                </p>
                {selectedTeam.latest_analysis_date && (
                  <p className="text-green-600 text-sm mt-1">
                    Ultimo: {new Date(selectedTeam.latest_analysis_date).toLocaleDateString("es-ES")}
                  </p>
                )}
              </div>
              <div className="space-y-2 mb-4">
                {selectedTeam.analyses.slice(0, 5).map((a) => (
                  <Link
                    key={a.analysis_id}
                    href={`/reports/${a.analysis_id}`}
                    className="block px-3 py-2 bg-gray-50 rounded hover:bg-gray-100 text-sm"
                  >
                    vs {a.opponent} — {new Date(a.date).toLocaleDateString("es-ES")}
                  </Link>
                ))}
              </div>
            </>
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
              <p className="text-amber-800 font-medium">
                No tenemos datos de {selectedTeam.team_name}
              </p>
              <p className="text-amber-600 text-sm mt-1">
                Sube un video de alguno de sus partidos para generar un analisis.
              </p>
              <Link
                href="/upload"
                className="inline-block mt-3 px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700"
              >
                Subir video del rival
              </Link>
            </div>
          )}

          {/* Mark as upcoming rival */}
          {!saved ? (
            <button
              onClick={handleMarkAsRival}
              className="w-full py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium"
            >
              Marcar como proximo rival
            </button>
          ) : (
            <div className="text-center py-2.5 text-green-700 font-medium text-sm">
              Rival registrado correctamente
            </div>
          )}
        </div>
      )}
    </div>
  );
}
