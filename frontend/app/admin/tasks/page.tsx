"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { listCeleryTasks, getCeleryTask, type CeleryTaskInfo } from "@/lib/api";

export default function AdminTasksPage() {
  const [active, setActive] = useState<CeleryTaskInfo[]>([]);
  const [reserved, setReserved] = useState<CeleryTaskInfo[]>([]);
  const [scheduled, setScheduled] = useState<CeleryTaskInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Task lookup
  const [lookupId, setLookupId] = useState("");
  const [lookupResult, setLookupResult] = useState<{
    id: string;
    status: string;
    result: unknown;
  } | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState("");

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadTasks = useCallback(async () => {
    try {
      const data = await listCeleryTasks();
      setActive(data.active);
      setReserved(data.reserved);
      setScheduled(data.scheduled);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar tareas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    intervalRef.current = setInterval(loadTasks, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loadTasks]);

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    if (!lookupId.trim()) return;
    setLookupLoading(true);
    setLookupError("");
    setLookupResult(null);
    try {
      const result = await getCeleryTask(lookupId.trim());
      setLookupResult(result);
    } catch (err) {
      setLookupError(err instanceof Error ? err.message : "Error al buscar tarea");
    } finally {
      setLookupLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Monitor Celery</h1>
          <p className="text-gray-500 text-sm mt-1">Auto-refresh cada 5 segundos</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-gray-500">En vivo</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {/* Task ID Lookup */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Buscar tarea por ID</h2>
        <form onSubmit={handleLookup} className="flex gap-3">
          <input
            type="text"
            value={lookupId}
            onChange={(e) => setLookupId(e.target.value)}
            placeholder="Task ID (UUID)"
            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={lookupLoading}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            {lookupLoading ? "Buscando..." : "Buscar"}
          </button>
        </form>
        {lookupError && (
          <p className="text-red-600 text-sm mt-2">{lookupError}</p>
        )}
        {lookupResult && (
          <div className="mt-3 bg-gray-50 rounded-lg p-4 text-sm">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <span className="text-gray-500">ID:</span>
                <p className="font-mono text-xs break-all">{lookupResult.id}</p>
              </div>
              <div>
                <span className="text-gray-500">Estado:</span>
                <p className="font-medium">{lookupResult.status}</p>
              </div>
              <div>
                <span className="text-gray-500">Resultado:</span>
                <p className="font-mono text-xs break-all">
                  {lookupResult.result != null
                    ? JSON.stringify(lookupResult.result)
                    : "null"}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Task sections */}
      <div className="space-y-6">
        <TaskSection title="Activas" tasks={active} color="green" />
        <TaskSection title="Reservadas" tasks={reserved} color="amber" />
        <TaskSection title="Programadas" tasks={scheduled} color="blue" />
      </div>
    </div>
  );
}

function TaskSection({
  title,
  tasks,
  color,
}: {
  title: string;
  tasks: CeleryTaskInfo[];
  color: string;
}) {
  const dotColor = `bg-${color}-500`;
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center gap-2 mb-4">
        <span className={`inline-block w-2 h-2 rounded-full ${dotColor}`} />
        <h2 className="text-sm font-semibold text-gray-700">
          {title} ({tasks.length})
        </h2>
      </div>
      {tasks.length === 0 ? (
        <p className="text-gray-400 text-sm">No hay tareas en esta cola</p>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="bg-gray-50 rounded-lg px-4 py-3 text-sm flex items-center gap-6"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{task.name}</p>
                <p className="text-gray-400 text-xs font-mono truncate">{task.id}</p>
              </div>
              <div className="text-gray-500 text-xs shrink-0">
                {task.args || "-"}
              </div>
              <div className="text-gray-400 text-xs shrink-0">
                {task.worker || "-"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
