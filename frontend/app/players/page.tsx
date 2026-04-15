"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listPlayers, type PlayerListItem } from "@/lib/api";
import { getClubId } from "@/lib/auth";
import { trackEvent } from "@/lib/posthog";

type SortKey = "name" | "shirt_number" | "position" | "scout_status";
type SortDir = "asc" | "desc";

export default function PlayersPage() {
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const clubId = getClubId() || "";

  useEffect(() => {
    if (!clubId) return;
    listPlayers(clubId)
      .then((data) => {
        setPlayers(data.players);
        trackEvent("players_list_viewed", { total: data.total });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Error al cargar jugadores"))
      .finally(() => setLoading(false));
  }, [clubId]);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sorted = [...players].sort((a, b) => {
    const valA = a[sortKey] ?? "";
    const valB = b[sortKey] ?? "";
    if (valA < valB) return sortDir === "asc" ? -1 : 1;
    if (valA > valB) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  function SortHeader({ label, field }: { label: string; field: SortKey }) {
    const active = sortKey === field;
    return (
      <th
        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700 select-none"
        onClick={() => handleSort(field)}
      >
        {label} {active ? (sortDir === "asc" ? "↑" : "↓") : ""}
      </th>
    );
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Jugadores</h1>
        <span className="text-sm text-gray-500">{players.length} jugadores</span>
      </div>

      {players.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-500">
          No hay jugadores registrados. Los jugadores se crean automaticamente al analizar partidos.
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <SortHeader label="Nombre" field="name" />
                <SortHeader label="Dorsal" field="shirt_number" />
                <SortHeader label="Posicion" field="position" />
                <SortHeader label="Scouting" field="scout_status" />
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sorted.map((player) => (
                <tr key={player.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{player.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {player.shirt_number != null ? `#${player.shirt_number}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{player.position || "—"}</td>
                  <td className="px-4 py-3 text-sm">
                    {player.has_scout_report ? (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        player.scout_status === "done"
                          ? "bg-green-100 text-green-800"
                          : player.scout_status === "error"
                          ? "bg-red-100 text-red-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}>
                        {player.scout_status === "done" ? "Evaluado" : player.scout_status === "error" ? "Error" : "En proceso"}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs">Sin evaluar</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-right">
                    {player.has_scout_report && player.scout_report_id && player.scout_status === "done" ? (
                      <Link
                        href={`/reports/scouting/${player.scout_report_id}`}
                        className="text-indigo-600 hover:text-indigo-800 text-xs font-medium"
                      >
                        Ver informe
                      </Link>
                    ) : !player.has_scout_report ? (
                      <Link
                        href={`/reports?scout_player=${player.id}`}
                        className="inline-flex items-center px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded text-xs font-medium hover:bg-indigo-100 transition-colors"
                      >
                        Generar scouting
                      </Link>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
