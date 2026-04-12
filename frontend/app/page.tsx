"use client";

import { useEffect, useState } from "react";
import { listReports, getClub, type ReportSummary, type Club } from "@/lib/api";
import { getClubId, isAuthenticated } from "@/lib/auth";

export default function HomePage() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    setAuthed(isAuthenticated());
  }, []);

  if (authed === null) return null; // SSR hydration guard
  if (!authed) return <Landing />;
  return <Dashboard />;
}

/* ===== Landing (visitantes no logueados) ===== */

function Landing() {
  return (
    <div className="min-h-screen bg-gray-50 -ml-64">
      {/* Hero */}
      <header className="bg-indigo-950 text-white">
        <nav className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">RFAF Analytics</h1>
          <div className="flex gap-4 text-sm">
            <a href="/pricing" className="text-indigo-200 hover:text-white transition-colors">
              Precios
            </a>
            <a href="/login" className="text-indigo-200 hover:text-white transition-colors">
              Entrar
            </a>
            <a
              href="/signup"
              className="bg-white text-indigo-950 px-4 py-1.5 rounded-lg font-medium hover:bg-indigo-100 transition-colors"
            >
              Registrarse
            </a>
          </div>
        </nav>

        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <h2 className="text-4xl md:text-5xl font-bold leading-tight">
            Analisis tactico con IA para tu club
          </h2>
          <p className="text-indigo-200 mt-4 text-lg max-w-2xl mx-auto">
            Sube un video de YouTube de cualquier partido y recibe un informe tactico profesional
            con xG, mapas de tiro, redes de pases y 12 secciones de analisis en minutos.
          </p>
          <div className="mt-8 flex gap-4 justify-center">
            <a
              href="/signup"
              className="bg-white text-indigo-950 px-8 py-3 rounded-lg font-semibold hover:bg-indigo-100 transition-colors"
            >
              Empezar gratis
            </a>
            <a
              href="/pricing"
              className="border border-indigo-400 text-indigo-200 px-8 py-3 rounded-lg font-medium hover:bg-indigo-900 transition-colors"
            >
              Ver planes
            </a>
          </div>
        </div>
      </header>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h3 className="text-2xl font-bold text-gray-900 text-center mb-12">
          Todo lo que tu cuerpo tecnico necesita
        </h3>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            {
              icon: "&#9917;",
              title: "Analisis de video con IA",
              desc: "Gemini 2.5 Flash extrae datos tacticos automaticamente de cualquier partido en YouTube.",
            },
            {
              icon: "&#128200;",
              title: "Metricas avanzadas",
              desc: "xG (Expected Goals), PPDA, Field Tilt, mapas de tiro y redes de pases con mplsoccer.",
            },
            {
              icon: "&#128196;",
              title: "Informes profesionales",
              desc: "Claude Sonnet genera informes de 12 secciones con PDF de branding RFAF listo para imprimir.",
            },
            {
              icon: "&#128172;",
              title: "Chatbot tactico",
              desc: "Haz preguntas sobre el informe y recibe respuestas contextuales del asistente IA.",
            },
            {
              icon: "&#128231;",
              title: "Email automatico",
              desc: "Recibe el informe completo con PDF adjunto en tu email al terminar el analisis.",
            },
            {
              icon: "&#128274;",
              title: "Seguro y privado",
              desc: "Cada club solo ve sus propios datos. Autenticacion JWT y aislamiento completo.",
            },
          ].map((f) => (
            <div key={f.title} className="bg-white rounded-xl shadow-sm border p-6">
              <p className="text-2xl" dangerouslySetInnerHTML={{ __html: f.icon }} />
              <h4 className="font-semibold text-gray-900 mt-3">{f.title}</h4>
              <p className="text-gray-500 text-sm mt-2">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-indigo-950 text-white py-16">
        <div className="max-w-3xl mx-auto text-center px-6">
          <h3 className="text-2xl font-bold">Listo para analizar tu proximo partido?</h3>
          <p className="text-indigo-200 mt-3">
            Plan Basico desde 49 EUR/mes. Incluye 3 analisis de partido con informe completo.
          </p>
          <a
            href="/signup"
            className="inline-block mt-6 bg-white text-indigo-950 px-8 py-3 rounded-lg font-semibold hover:bg-indigo-100 transition-colors"
          >
            Crear cuenta
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-6 py-8 text-center text-xs text-gray-400">
        RFAF Analytics Platform v2.0 &middot; Real Federacion Aragonesa de Futbol &middot; 2026
      </footer>
    </div>
  );
}

/* ===== Dashboard (usuarios logueados) ===== */

function Dashboard() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [club, setClub] = useState<Club | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const clubId = getClubId();
    if (!clubId) return;

    async function load() {
      try {
        const [r, c] = await Promise.all([
          listReports(clubId!),
          getClub(clubId!),
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
  const processing = reports.filter(
    (r) => r.status === "processing" || r.status === "pending",
  ).length;

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
          {club.name} &middot; Plan {club.plan} &middot; {club.analisis_mes_actual} analisis este
          mes
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
          <p className="text-sm text-gray-500">Total analisis</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{reports.length}</p>
        </div>
      </div>

      {/* Quick actions */}
      <div className="mt-8">
        <a
          href="/analyze"
          className="inline-flex items-center gap-2 bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
        >
          Nuevo analisis de partido
        </a>
      </div>

      {/* Recent reports */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Informes recientes</h2>
        {reports.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-500">
            No hay informes todavia. Analiza tu primer partido!
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
                        : "\u2014"}
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
                          Ver informe &rarr;
                        </a>
                      ) : r.status === "pending" || r.status === "processing" ? (
                        <a
                          href={`/analyze/${r.analysis_id}`}
                          className="text-amber-600 hover:text-amber-800 text-sm font-medium"
                        >
                          Ver progreso &rarr;
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
