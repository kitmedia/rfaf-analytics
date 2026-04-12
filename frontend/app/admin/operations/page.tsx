"use client";

import { useEffect, useState, useCallback } from "react";
import {
  triggerBackup,
  listBackups,
  triggerXgTraining,
  getXgModelStatus,
  getCeleryTask,
  type BackupInfo,
  type MlModelStatus,
} from "@/lib/api";

export default function AdminOperationsPage() {
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [backupsLoading, setBackupsLoading] = useState(true);
  const [backupTaskId, setBackupTaskId] = useState<string | null>(null);
  const [backupTaskStatus, setBackupTaskStatus] = useState("");
  const [backupError, setBackupError] = useState("");

  const [modelStatus, setModelStatus] = useState<MlModelStatus | null>(null);
  const [modelLoading, setModelLoading] = useState(true);
  const [trainTaskId, setTrainTaskId] = useState<string | null>(null);
  const [trainTaskStatus, setTrainTaskStatus] = useState("");
  const [modelError, setModelError] = useState("");

  const loadBackups = useCallback(async () => {
    try {
      setBackupsLoading(true);
      const data = await listBackups();
      setBackups(data);
      setBackupError("");
    } catch (err) {
      setBackupError(err instanceof Error ? err.message : "Error al cargar backups");
    } finally {
      setBackupsLoading(false);
    }
  }, []);

  const loadModelStatus = useCallback(async () => {
    try {
      setModelLoading(true);
      const data = await getXgModelStatus();
      setModelStatus(data);
      setModelError("");
    } catch (err) {
      setModelError(err instanceof Error ? err.message : "Error al cargar estado del modelo");
    } finally {
      setModelLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBackups();
    loadModelStatus();
  }, [loadBackups, loadModelStatus]);

  // Poll task status
  useEffect(() => {
    if (!backupTaskId) return;
    const interval = setInterval(async () => {
      try {
        const result = await getCeleryTask(backupTaskId);
        setBackupTaskStatus(result.status);
        if (result.status === "SUCCESS" || result.status === "FAILURE") {
          clearInterval(interval);
          setBackupTaskId(null);
          if (result.status === "SUCCESS") loadBackups();
        }
      } catch {
        clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [backupTaskId, loadBackups]);

  useEffect(() => {
    if (!trainTaskId) return;
    const interval = setInterval(async () => {
      try {
        const result = await getCeleryTask(trainTaskId);
        setTrainTaskStatus(result.status);
        if (result.status === "SUCCESS" || result.status === "FAILURE") {
          clearInterval(interval);
          setTrainTaskId(null);
          if (result.status === "SUCCESS") loadModelStatus();
        }
      } catch {
        clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [trainTaskId, loadModelStatus]);

  async function handleBackup() {
    try {
      setBackupError("");
      setBackupTaskStatus("PENDING");
      const result = await triggerBackup();
      setBackupTaskId(result.task_id);
    } catch (err) {
      setBackupError(err instanceof Error ? err.message : "Error al iniciar backup");
      setBackupTaskStatus("");
    }
  }

  async function handleRetrain() {
    try {
      setModelError("");
      setTrainTaskStatus("PENDING");
      const result = await triggerXgTraining();
      setTrainTaskId(result.task_id);
    } catch (err) {
      setModelError(err instanceof Error ? err.message : "Error al iniciar entrenamiento");
      setTrainTaskStatus("");
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Operaciones del sistema</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Database Backup */}
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">Backup de base de datos</h2>
            <button
              onClick={handleBackup}
              disabled={!!backupTaskId}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {backupTaskId ? "Ejecutando..." : "Crear backup"}
            </button>
          </div>

          {backupTaskStatus && (
            <div className="bg-blue-50 border border-blue-200 text-blue-700 px-3 py-2 rounded-lg mb-4 text-sm flex items-center gap-2">
              {backupTaskStatus === "PENDING" || backupTaskStatus === "STARTED" ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
              ) : null}
              Estado: {backupTaskStatus}
            </div>
          )}

          {backupError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg mb-4 text-sm">
              {backupError}
            </div>
          )}

          {backupsLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" />
            </div>
          ) : backups.length === 0 ? (
            <p className="text-gray-400 text-sm">No hay backups recientes</p>
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {backups.map((backup) => (
                <div
                  key={backup.key}
                  className="bg-gray-50 rounded-lg px-4 py-3 flex items-center justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900 truncate max-w-xs">
                      {backup.key}
                    </p>
                    <p className="text-xs text-gray-400">
                      {new Date(backup.last_modified).toLocaleString("es-ES")}
                    </p>
                  </div>
                  <span className="text-xs text-gray-500 font-mono">
                    {formatBytes(backup.size_bytes)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* xG Model */}
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">Modelo xG (XGBoost)</h2>
            <button
              onClick={handleRetrain}
              disabled={!!trainTaskId}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {trainTaskId ? "Entrenando..." : "Reentrenar"}
            </button>
          </div>

          {trainTaskStatus && (
            <div className="bg-blue-50 border border-blue-200 text-blue-700 px-3 py-2 rounded-lg mb-4 text-sm flex items-center gap-2">
              {trainTaskStatus === "PENDING" || trainTaskStatus === "STARTED" ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
              ) : null}
              Estado: {trainTaskStatus}
            </div>
          )}

          {modelError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg mb-4 text-sm">
              {modelError}
            </div>
          )}

          {modelLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600" />
            </div>
          ) : modelStatus ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-500">Estado</p>
                  <p className="text-sm font-medium mt-1">
                    {modelStatus.exists ? (
                      <span className="text-green-700">Disponible</span>
                    ) : (
                      <span className="text-red-700">No encontrado</span>
                    )}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-500">Tamano</p>
                  <p className="text-sm font-medium mt-1">
                    {modelStatus.exists && modelStatus.size_bytes ? formatBytes(modelStatus.size_bytes) : "-"}
                  </p>
                </div>
              </div>

              {modelStatus.last_modified && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-xs text-gray-500">Ultima actualizacion</p>
                  <p className="text-sm font-medium mt-1">
                    {new Date(modelStatus.last_modified).toLocaleString("es-ES")}
                  </p>
                </div>
              )}

              {modelStatus.metrics && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500">Brier Score</p>
                    <p className="text-lg font-bold text-indigo-600 mt-1">
                      {modelStatus.metrics.brier_score.toFixed(4)}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-xs text-gray-500">AUC</p>
                    <p className="text-lg font-bold text-indigo-600 mt-1">
                      {modelStatus.metrics.auc.toFixed(4)}
                    </p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No se pudo obtener el estado del modelo</p>
          )}
        </div>
      </div>
    </div>
  );
}
