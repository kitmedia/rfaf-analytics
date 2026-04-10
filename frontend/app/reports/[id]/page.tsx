"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getReport, getPdfUrl, type ReportDetail } from "@/lib/api";
import { trackEvent } from "@/lib/posthog";
import Markdown from "react-markdown";

export default function ReportPage() {
  const params = useParams();
  const id = params.id as string;

  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"informe" | "graficas" | "datos">("informe");

  useEffect(() => {
    async function load() {
      try {
        const data = await getReport(id);
        setReport(data);
        trackEvent("report_viewed", { analysis_id: id, status: data.status });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar el informe");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || "Informe no encontrado"}
        </div>
      </div>
    );
  }

  const charts = report.charts_json || {};
  const chartEntries = Object.entries(charts);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {report.equipo_local} vs {report.equipo_visitante}
          </h1>
          {report.competicion && (
            <p className="text-gray-500 mt-1">{report.competicion}</p>
          )}
          <p className="text-gray-400 text-sm mt-1">
            {new Date(report.created_at).toLocaleDateString("es-ES", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        </div>
        {report.status === "done" && (
          <a
            href={getPdfUrl(id)}
            className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
          >
            📄 Descargar PDF
          </a>
        )}
      </div>

      {/* xG Cards */}
      {report.xg_local != null && report.xg_visitante != null && (
        <div className="grid grid-cols-2 gap-4 mt-6">
          <div className="bg-white rounded-xl shadow-sm border p-5 text-center">
            <p className="text-sm text-gray-500">{report.equipo_local}</p>
            <p className="text-3xl font-bold text-indigo-600 mt-1">
              {report.xg_local.toFixed(2)}
            </p>
            <p className="text-xs text-gray-400 mt-1">xG</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-5 text-center">
            <p className="text-sm text-gray-500">{report.equipo_visitante}</p>
            <p className="text-3xl font-bold text-red-500 mt-1">
              {report.xg_visitante.toFixed(2)}
            </p>
            <p className="text-xs text-gray-400 mt-1">xG</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="mt-8 border-b">
        <nav className="flex gap-8">
          {(
            [
              ["informe", "Informe táctico"],
              ["graficas", `Gráficas (${chartEntries.length})`],
              ["datos", "Datos"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === key
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="mt-6">
        {activeTab === "informe" && (
          <div className="bg-white rounded-xl shadow-sm border p-8 prose prose-indigo max-w-none">
            {report.contenido_md ? (
              <Markdown>{report.contenido_md}</Markdown>
            ) : (
              <p className="text-gray-500">
                El informe aún no está disponible.
              </p>
            )}
          </div>
        )}

        {activeTab === "graficas" && (
          <div className="space-y-6">
            {chartEntries.length === 0 ? (
              <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-500">
                No hay gráficas disponibles para este informe.
              </div>
            ) : (
              chartEntries.map(([name, base64]) => (
                <div key={name} className="bg-white rounded-xl shadow-sm border p-6">
                  <h3 className="text-sm font-medium text-gray-700 mb-3 capitalize">
                    {name.replace(/_/g, " ")}
                  </h3>
                  <img
                    src={`data:image/png;base64,${base64}`}
                    alt={name}
                    className="w-full max-w-2xl mx-auto"
                  />
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "datos" && (
          <div className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Estado:</span>{" "}
                <span className="font-medium">{report.status}</span>
              </div>
              <div>
                <span className="text-gray-500">ID:</span>{" "}
                <span className="font-mono text-xs">{report.analysis_id}</span>
              </div>
              {report.cost_gemini != null && (
                <div>
                  <span className="text-gray-500">Coste Gemini:</span>{" "}
                  <span className="font-medium">{report.cost_gemini.toFixed(4)} EUR</span>
                </div>
              )}
              {report.cost_claude != null && (
                <div>
                  <span className="text-gray-500">Coste Claude:</span>{" "}
                  <span className="font-medium">{report.cost_claude.toFixed(4)} EUR</span>
                </div>
              )}
              {report.cost_gemini != null && report.cost_claude != null && (
                <div>
                  <span className="text-gray-500">Coste total:</span>{" "}
                  <span className="font-bold text-indigo-600">
                    {(report.cost_gemini + report.cost_claude).toFixed(4)} EUR
                  </span>
                </div>
              )}
              {report.duration_s != null && (
                <div>
                  <span className="text-gray-500">Duración:</span>{" "}
                  <span className="font-medium">{report.duration_s.toFixed(1)}s</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
