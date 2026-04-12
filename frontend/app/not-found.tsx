import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <p className="text-6xl font-bold text-indigo-600">404</p>
        <h1 className="text-2xl font-semibold text-gray-900 mt-4">
          Pagina no encontrada
        </h1>
        <p className="text-gray-500 mt-2">
          La pagina que buscas no existe o ha sido movida.
        </p>
        <Link
          href="/"
          className="inline-block mt-6 bg-indigo-600 text-white px-6 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
        >
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}
