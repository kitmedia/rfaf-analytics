"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getScoutReport, getScoutPdfUrl, type ScoutReportDetail } from "@/lib/api";
import { getClubId } from "@/lib/auth";
import { trackEvent } from "@/lib/posthog";
import Markdown from "react-markdown";

function parseVerdict(markdown: string): string | null {
  const match = markdown.match(/Recomendaci[oó]n:\s*(Fichar|Seguir observando|Descartar)/i);
  return match ? match[1] : null;
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const colors: Record<string, string> = {
    fichar: "bg-green-100 text-green-800 border-green-300",
    "seguir observando": "bg-amber-100 text-amber-800 border-amber-300",
    descartar: "bg-red-100 text-red-800 border-red-300",
  };
  const colorClass = colors[verdict.toLowerCase()] || "bg-gray-100 text-gray-800 border-gray-300";

  return (
    <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-semibold border ${colorClass}`}>
      {verdict}
    </span>
  );
}

export default function ScoutingProfilePage() {
  const params = useParams();
  const id = params.id as string;
  const clubId = getClubId() || "";

  const [report, setReport] = useState<ScoutReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!clubId) return;
    async function load() {
      try {
        const data = await getScoutReport(id, clubId);
        setReport(data);
        trackEvent("scout_report_viewed", { scout_report_id: id });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar el informe de scouting");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id, clubId]);

  // Polling for pending/processing reports
  useEffect(() => {
    if (!report || !clubId) return;
    if (report.status !== "pending" && report.status !== "processing") return;

    const poll = setInterval(async () => {
      try {
        const updated = await getScoutReport(id, clubId);
        setReport(updated);
        if (updated.status === "done" || updated.status === "error") {
          clearInterval(poll);
        }
      } catch {
        // keep polling
      }
    }, 5000);

    return () => clearInterval(poll);
  }, [report?.status, id, clubId]);

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
          {error || "Informe de scouting no encontrado"}
        </div>
      </div>
    );
  }

  if (report.status === "pending" || report.status === "processing") {
    return (
      <div className="p-8">
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-gray-700 font-medium">Generando informe de scouting...</p>
          <p className="text-gray-500 text-sm mt-1">
            {report.player_name}{report.player_number ? ` (#${report.player_number})` : ""}
          </p>
        </div>
      </div>
    );
  }

  if (report.status === "error") {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          Error al generar el informe de scouting. Inténtalo de nuevo.
        </div>
      </div>
    );
  }

  const verdict = report.contenido_md ? parseVerdict(report.contenido_md) : null;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {report.player_name}
            {report.player_number != null && (
              <span className="text-gray-400 ml-2">#{report.player_number}</span>
            )}
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Informe de scouting — {new Date(report.created_at).toLocaleDateString("es-ES", {
              year: "numeric", month: "long", day: "numeric",
            })}
          </p>
          {verdict && (
            <div className="mt-3">
              <VerdictBadge verdict={verdict} />
            </div>
          )}
        </div>
        {report.contenido_md && (
          <a
            href={getScoutPdfUrl(id, clubId)}
            onClick={() => trackEvent("scout_pdf_download", { scout_report_id: id })}
            className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
          >
            Descargar PDF
          </a>
        )}
      </div>

      {/* Content */}
      {report.contenido_md ? (
        <div className="bg-white rounded-xl shadow-sm border p-8 prose prose-indigo max-w-none">
          <Markdown>{report.contenido_md}</Markdown>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-500">
          El informe de scouting no tiene contenido.
        </div>
      )}

      {/* Cost */}
      {report.cost_eur != null && (
        <div className="mt-4 text-right text-xs text-gray-400">
          Coste: {report.cost_eur.toFixed(4)} EUR
        </div>
      )}
    </div>
  );
}
