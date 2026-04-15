"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { getReport, getPdfUrl, chatAboutReport, generateTrainingPlan, markExerciseComplete, unmarkExercise, getExercisesByAnalysis, getWeeklySummary, getTrends, getExerciseImpact, retrySection, type ReportDetail, type ChatResponse, type ExerciseStatus, type TrendsResponse, type ImpactResponse } from "@/lib/api";
import { trackEvent } from "@/lib/posthog";
import { getClubId } from "@/lib/auth";
import Markdown from "react-markdown";
import { parseTrainingPlan } from "@/lib/parseTrainingPlan";
import ExerciseCard from "@/components/training/ExerciseCard";
import WeeklyProgressBanner from "@/components/training/WeeklyProgressBanner";
import TrendChart from "@/components/training/TrendChart";

export default function ReportPage() {
  const params = useParams();
  const id = params.id as string;

  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"informe" | "graficas" | "datos" | "chat" | "plan" | "evolucion">("informe");
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [planError, setPlanError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

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

  async function handleGeneratePlan() {
    const clubId = getClubId();
    if (!clubId) return;
    setGeneratingPlan(true);
    setPlanError("");
    try {
      await generateTrainingPlan(id, clubId);
      trackEvent("training_plan_requested", { analysis_id: id });
      // Poll for completion (with cleanup refs)
      pollRef.current = setInterval(async () => {
        try {
          const updated = await getReport(id);
          if (updated.training_plan_json) {
            if (updated.training_plan_json.contenido_md) {
              setReport(updated);
              setActiveTab("plan");
            } else {
              // Error marker from failed task
              setPlanError("Error al generar el plan de entrenamiento. Inténtalo de nuevo.");
            }
            setGeneratingPlan(false);
            if (pollRef.current) clearInterval(pollRef.current);
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
          }
        } catch {
          // keep polling
        }
      }, 5000);
      // Stop polling after 3 minutes
      timeoutRef.current = setTimeout(() => {
        if (pollRef.current) clearInterval(pollRef.current);
        setGeneratingPlan(false);
        setPlanError("La generación está tardando más de lo esperado. Recarga la página en unos minutos.");
      }, 180000);
    } catch (err) {
      setPlanError(err instanceof Error ? err.message : "Error al generar el plan");
      setGeneratingPlan(false);
    }
  }

  const charts = report.charts_json || {};
  const chartEntries = Object.entries(charts);
  const isDone = report.status === "done";

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
        {isDone && (
          <div className="flex gap-2">
            {!report.training_plan_json && (
              <button
                onClick={handleGeneratePlan}
                disabled={generatingPlan}
                className="inline-flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50"
              >
                {generatingPlan ? "Generando..." : "Generar plan de entrenamiento"}
              </button>
            )}
            <a
              href={getPdfUrl(id)}
              onClick={() => trackEvent("pdf_download_clicked", { analysis_id: id })}
              className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
            >
              Descargar PDF
            </a>
          </div>
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
        <nav className="flex gap-8 overflow-x-auto flex-nowrap -mb-px">
          {(
            [
              ["informe", "Informe táctico"],
              ["graficas", `Gráficas (${chartEntries.length})`],
              ...(report.training_plan_json ? [["plan", "Plan de entrenamiento"] as const] : []),
              ...(isDone ? [["evolucion", "Evolución"] as const] : []),
              ["chat", "Chat táctico"],
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

      {/* Degraded report banner */}
      {report.sections_available && Object.values(report.sections_available).some(v => v === false) && (
        <div className="mt-6 bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg text-sm">
          Algunas secciones del informe no pudieron generarse. Las secciones disponibles se muestran normalmente.
        </div>
      )}

      {/* Tab content */}
      <div className="mt-6">
        {activeTab === "informe" && (
          report.sections_available?.narrative === false ? (
            <SectionUnavailableBanner
              section="narrative"
              analysisId={id}
              onRetryComplete={async () => { const updated = await getReport(id); setReport(updated); }}
            />
          ) : (
            <div className="bg-white rounded-xl shadow-sm border p-8 prose prose-indigo max-w-none">
              {report.contenido_md ? (
                <Markdown>{report.contenido_md}</Markdown>
              ) : (
                <p className="text-gray-500">
                  El informe aún no está disponible.
                </p>
              )}
            </div>
          )
        )}

        {activeTab === "graficas" && (
          report.sections_available?.charts === false ? (
            <SectionUnavailableBanner
              section="charts"
              analysisId={id}
              onRetryComplete={async () => { const updated = await getReport(id); setReport(updated); }}
            />
          ) : (
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
          )
        )}

        {planError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {planError}
          </div>
        )}

        {activeTab === "plan" && report.training_plan_json && (
          <TrainingPlanTab
            markdown={report.training_plan_json.contenido_md}
            analysisId={id}
            onNavigateToReport={() => setActiveTab("informe")}
          />
        )}

        {activeTab === "evolucion" && (
          <EvolucionTab />
        )}

        {activeTab === "chat" && (
          <ChatPanel analysisId={id} isDone={isDone} />
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

// --- Section Unavailable Banner ---

function SectionUnavailableBanner({
  section,
  analysisId,
  onRetryComplete,
}: {
  section: string;
  analysisId: string;
  onRetryComplete: () => void;
}) {
  const [retrying, setRetrying] = useState(false);
  const clubId = getClubId() || "";

  const sectionNames: Record<string, string> = {
    extraction: "Análisis de vídeo",
    narrative: "Informe táctico",
    charts: "Gráficas",
    pdf: "PDF",
  };

  async function handleRetry() {
    if (!clubId) return;
    setRetrying(true);
    try {
      await retrySection(analysisId, clubId, section);
      // Poll for completion
      const poll = setInterval(async () => {
        try {
          const updated = await getReport(analysisId);
          if (updated.sections_available?.[section] === true) {
            clearInterval(poll);
            setRetrying(false);
            onRetryComplete();
          }
        } catch { /* keep polling */ }
      }, 5000);
      setTimeout(() => { clearInterval(poll); setRetrying(false); }, 120000);
    } catch {
      setRetrying(false);
    }
  }

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-8 text-center">
      <p className="text-amber-800 font-medium mb-2">
        {sectionNames[section] || section}: esta sección no pudo generarse
      </p>
      <p className="text-amber-600 text-sm mb-4">
        Hubo un problema al procesar esta parte del análisis. Puedes intentar generarla de nuevo.
      </p>
      <button
        onClick={handleRetry}
        disabled={retrying}
        className="inline-flex items-center px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors text-sm font-medium disabled:opacity-50"
      >
        {retrying ? "Reintentando..." : "Reintentar"}
      </button>
    </div>
  );
}

// --- Evolucion Tab ---

function EvolucionTab() {
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [impact, setImpact] = useState<ImpactResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const clubId = getClubId() || "";

  useEffect(() => {
    if (!clubId) return;
    Promise.all([
      getTrends(clubId).catch(() => null),
      getExerciseImpact(clubId).catch(() => null),
    ]).then(([t, i]) => {
      setTrends(t);
      setImpact(i);
      setLoading(false);
    });
  }, [clubId]);

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto" />
      </div>
    );
  }

  if (!trends || !trends.has_enough_data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-500">
        <p className="text-lg font-medium mb-2">Datos insuficientes</p>
        <p>Necesitas al menos 3 informes para ver tendencias. Analiza más partidos para desbloquear esta función.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Impact badge */}
      {impact?.has_impact && impact.message && (
        <div className={`rounded-xl border p-4 ${
          (impact.improvement_pct ?? 0) > 0
            ? "bg-green-50 border-green-200"
            : "bg-amber-50 border-amber-200"
        }`}>
          <p className={`text-sm font-medium ${
            (impact.improvement_pct ?? 0) > 0 ? "text-green-800" : "text-amber-800"
          }`}>
            {impact.message}
          </p>
        </div>
      )}

      {/* TrendChart */}
      <TrendChart data={trends.weeks} />
    </div>
  );
}

// --- Training Plan Tab ---

function TrainingPlanTab({
  markdown,
  analysisId,
  onNavigateToReport,
}: {
  markdown: string;
  analysisId: string;
  onNavigateToReport: () => void;
}) {
  const parsed = useMemo(() => parseTrainingPlan(markdown), [markdown]);
  const [completedExercises, setCompletedExercises] = useState<Set<string>>(new Set());
  const [weeklySummary, setWeeklySummary] = useState<{ completed_count: number; total_count: number } | null>(null);
  const clubId = getClubId() || "";

  // Load completed exercises and weekly summary
  useEffect(() => {
    if (!clubId) return;
    getExercisesByAnalysis(analysisId, clubId).then((data) => {
      setCompletedExercises(new Set(data.exercises.filter((e) => e.completed).map((e) => e.exercise_name)));
    }).catch(() => {});
    getWeeklySummary(clubId).then(setWeeklySummary).catch(() => {});
  }, [analysisId, clubId]);

  async function handleToggleComplete(exerciseName: string, completed: boolean) {
    if (!clubId) return;
    // Optimistic update
    setCompletedExercises((prev) => {
      const next = new Set(prev);
      if (completed) next.add(exerciseName);
      else next.delete(exerciseName);
      return next;
    });
    try {
      if (completed) {
        await markExerciseComplete(clubId, analysisId, exerciseName);
      } else {
        await unmarkExercise(clubId, analysisId, exerciseName);
      }
      // Refresh weekly summary
      const summary = await getWeeklySummary(clubId);
      setWeeklySummary(summary);
    } catch {
      // Revert on failure
      setCompletedExercises((prev) => {
        const next = new Set(prev);
        if (completed) next.delete(exerciseName);
        else next.add(exerciseName);
        return next;
      });
    }
  }

  // Fallback: render raw markdown if parsing fails
  if (!parsed) {
    return (
      <div className="bg-white rounded-xl shadow-sm border p-8 prose prose-indigo max-w-none">
        <Markdown>{markdown}</Markdown>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Weekly Progress Banner */}
      {weeklySummary && weeklySummary.total_count > 0 && (
        <WeeklyProgressBanner
          completedCount={weeklySummary.completed_count}
          totalCount={weeklySummary.total_count}
        />
      )}

      {/* Seccion 1: Analisis Didactico */}
      {parsed.analisisDidactico && (
        <div className="bg-white rounded-xl shadow-sm border p-6 prose prose-indigo max-w-none">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Análisis Didáctico</h2>
          <Markdown>{parsed.analisisDidactico}</Markdown>
        </div>
      )}

      {/* Seccion 3: Conceptos Tacticos (areas prioritarias) */}
      {parsed.conceptosTacticos && (
        <div className="bg-indigo-50 rounded-xl border border-indigo-100 p-6">
          <h2 className="text-lg font-semibold text-indigo-900 mb-3">Áreas Prioritarias</h2>
          <div className="prose prose-indigo prose-sm max-w-none">
            <Markdown>{parsed.conceptosTacticos}</Markdown>
          </div>
        </div>
      )}

      {/* Seccion 2: Ejercicios */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Ejercicios de Entrenamiento ({parsed.ejercicios.length})
        </h2>
        <div className="space-y-4">
          {parsed.ejercicios.map((exercise, i) => (
            <ExerciseCard
              key={`${i}-${exercise.name}`}
              exercise={exercise}
              index={i}
              completed={completedExercises.has(exercise.name)}
              onToggleComplete={handleToggleComplete}
              onNavigateToReport={onNavigateToReport}
            />
          ))}
        </div>
      </div>

      {/* Seccion 4: Plan Semanal */}
      {parsed.planSemanal && (
        <div className="bg-white rounded-xl shadow-sm border p-6 prose prose-indigo max-w-none">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Plan Semanal Sugerido</h2>
          <Markdown>{parsed.planSemanal}</Markdown>
        </div>
      )}

      {/* Seccion 5: Recursos */}
      {parsed.recursos && (
        <div className="bg-white rounded-xl shadow-sm border p-6 prose prose-indigo max-w-none">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Recursos Adicionales</h2>
          <Markdown>{parsed.recursos}</Markdown>
        </div>
      )}
    </div>
  );
}

// --- Chat Component ---

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

function ChatPanel({ analysisId, isDone }: { analysisId: string; isDone: boolean }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const suggestions = [
    "¿Cómo neutralizo al delantero rival en el próximo partido?",
    "¿Qué debilidades tiene el equipo visitante?",
    "¿Qué ejercicios recomiendas para mejorar el pressing?",
    "Resume las 3 conclusiones más importantes",
  ];

  async function sendMessage(question: string) {
    if (!question.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await chatAboutReport(analysisId, question, getClubId() || "");
      trackEvent("chatbot_query", { analysis_id: analysisId, query_length: question.length });
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: err instanceof Error ? err.message : "Error al consultar el chatbot." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!isDone) {
    return (
      <div className="bg-white rounded-xl shadow-sm border p-8 text-center text-gray-500">
        El chatbot táctico estará disponible cuando el informe se complete.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden flex flex-col" style={{ height: "600px" }}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-400 text-sm mb-4">
              Pregunta lo que quieras sobre este partido. El chatbot tiene acceso al informe completo.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-xs bg-indigo-50 text-indigo-600 px-3 py-1.5 rounded-full hover:bg-indigo-100 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-md"
                  : "bg-gray-100 text-gray-800 rounded-bl-md"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="prose prose-sm max-w-none">
                  <Markdown>{msg.content}</Markdown>
                </div>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-bl-md">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Pregunta sobre el partido..."
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 text-sm"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            Enviar
          </button>
        </form>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Powered by Claude Haiku 4.5
        </p>
      </div>
    </div>
  );
}
