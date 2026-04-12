"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md">
        <p className="text-6xl font-bold text-red-500">Error</p>
        <h1 className="text-2xl font-semibold text-gray-900 mt-4">
          Algo ha salido mal
        </h1>
        <p className="text-gray-500 mt-2">
          {error.message || "Se ha producido un error inesperado."}
        </p>
        <div className="flex gap-3 justify-center mt-6">
          <button
            onClick={reset}
            className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
          >
            Intentar de nuevo
          </button>
          <a
            href="/"
            className="bg-gray-100 text-gray-900 px-6 py-2.5 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
          >
            Volver al inicio
          </a>
        </div>
      </div>
    </div>
  );
}
