"use client";

import { useCallback, useRef, useState } from "react";

const ALLOWED_EXTENSIONS = ["mp4", "mov", "avi"];
const MAX_SIZE_GB = 5;
const MAX_SIZE_BYTES = MAX_SIZE_GB * 1024 * 1024 * 1024;

interface VideoUploaderProps {
  onFileSelected: (file: File) => void;
  uploading: boolean;
  uploadProgress: number;
  error: string;
}

export default function VideoUploader({
  onFileSelected,
  uploading,
  uploadProgress,
  error,
}: VideoUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [validationError, setValidationError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function validateFile(file: File): string | null {
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Formato no soportado: .${ext}. Usa MP4, MOV o AVI.`;
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `El archivo excede ${MAX_SIZE_GB} GB.`;
    }
    return null;
  }

  function handleFile(file: File) {
    const err = validateFile(file);
    if (err) {
      setValidationError(err);
      return;
    }
    setValidationError("");
    onFileSelected(file);
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, []);

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          dragOver
            ? "border-indigo-400 bg-indigo-50"
            : "border-gray-300 bg-gray-50 hover:border-gray-400"
        } ${uploading ? "pointer-events-none opacity-60" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.avi"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
          disabled={uploading}
        />
        <svg className="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-gray-700 font-medium">
          {uploading ? "Subiendo video..." : "Arrastra tu video aquí o haz click para seleccionar"}
        </p>
        <p className="text-gray-400 text-sm mt-1">
          MP4, MOV o AVI — máximo {MAX_SIZE_GB} GB
        </p>
      </div>

      {/* Upload progress */}
      {uploading && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Subiendo video...</span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Errors */}
      {(validationError || error) && (
        <div className="mt-3 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {validationError || error}
        </div>
      )}
    </div>
  );
}
