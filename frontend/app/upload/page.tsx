"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadVideo } from "@/lib/api";
import { getClubId } from "@/lib/auth";
import { trackEvent } from "@/lib/posthog";
import VideoUploader from "@/components/analysis/VideoUploader";

export default function UploadPage() {
  const router = useRouter();
  const clubId = getClubId() || "";

  const [equipoLocal, setEquipoLocal] = useState("");
  const [equipoVisitante, setEquipoVisitante] = useState("");
  const [competicion, setCompeticion] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedFile || !equipoLocal || !equipoVisitante || !clubId) return;

    setUploading(true);
    setError("");
    setUploadProgress(10);

    try {
      // Simulate progress (real progress would need XMLHttpRequest)
      setUploadProgress(30);
      const result = await uploadVideo(
        selectedFile,
        clubId,
        equipoLocal,
        equipoVisitante,
        competicion || undefined,
      );
      setUploadProgress(100);
      trackEvent("video_uploaded", {
        analysis_id: result.analysis_id,
        file_size_mb: Math.round(selectedFile.size / (1024 * 1024)),
      });

      // Redirect to status page
      router.push(`/reports/${result.analysis_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al subir el video");
      setUploading(false);
      setUploadProgress(0);
    }
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Subir video de partido</h1>
      <p className="text-gray-500 mb-8">
        Sube un video directamente sin necesidad de YouTube. El análisis se iniciará automáticamente.
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Teams */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Equipo local *</label>
            <input
              type="text"
              value={equipoLocal}
              onChange={(e) => setEquipoLocal(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
              required
              disabled={uploading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Equipo visitante *</label>
            <input
              type="text"
              value={equipoVisitante}
              onChange={(e) => setEquipoVisitante(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
              required
              disabled={uploading}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Competición (opcional)</label>
          <input
            type="text"
            value={competicion}
            onChange={(e) => setCompeticion(e.target.value)}
            placeholder="Ej: Tercera RFEF, Regional Preferente"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
            disabled={uploading}
          />
        </div>

        {/* Video Uploader */}
        <VideoUploader
          onFileSelected={setSelectedFile}
          uploading={uploading}
          uploadProgress={uploadProgress}
          error={error}
        />

        {selectedFile && !uploading && (
          <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600">
            Archivo seleccionado: <span className="font-medium">{selectedFile.name}</span>
            {" "}({(selectedFile.size / (1024 * 1024)).toFixed(0)} MB)
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={!selectedFile || !equipoLocal || !equipoVisitante || uploading}
          className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50"
        >
          {uploading ? "Subiendo y analizando..." : "Subir y analizar partido"}
        </button>
      </form>
    </div>
  );
}
