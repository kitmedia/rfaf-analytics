"use client";

import { useEffect, useState, useCallback } from "react";
import { listAdminFeedbacks, type AdminFeedbackItem } from "@/lib/api";

const categories = [
  { key: "", label: "Todas las categorias" },
  { key: "usabilidad", label: "Usabilidad" },
  { key: "precision", label: "Precision" },
  { key: "velocidad", label: "Velocidad" },
  { key: "contenido", label: "Contenido" },
  { key: "otro", label: "Otro" },
];

const categoryColors: Record<string, string> = {
  usabilidad: "bg-blue-100 text-blue-800",
  precision: "bg-purple-100 text-purple-800",
  velocidad: "bg-amber-100 text-amber-800",
  contenido: "bg-green-100 text-green-800",
  otro: "bg-gray-100 text-gray-800",
};

function Stars({ rating }: { rating: number }) {
  return (
    <span className="inline-flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <span
          key={star}
          className={`text-sm ${star <= rating ? "text-amber-400" : "text-gray-300"}`}
        >
          &#9733;
        </span>
      ))}
    </span>
  );
}

export default function AdminFeedbackPage() {
  const [feedbacks, setFeedbacks] = useState<AdminFeedbackItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listAdminFeedbacks(undefined, categoryFilter || undefined);
      setFeedbacks(data.feedbacks);
      setTotal(data.total);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar feedback");
    } finally {
      setLoading(false);
    }
  }, [categoryFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Feedback</h1>
          <p className="text-gray-500 text-sm mt-1">{total} respuestas de feedback</p>
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {categories.map((c) => (
            <option key={c.key} value={c.key}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center min-h-[200px]">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Club</th>
                <th className="px-4 py-3 font-medium">Categoria</th>
                <th className="px-4 py-3 font-medium">Valoracion</th>
                <th className="px-4 py-3 font-medium">Comentario</th>
                <th className="px-4 py-3 font-medium">Fecha</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {feedbacks.map((fb) => (
                <tr key={fb.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{fb.club_name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${categoryColors[fb.category] || "bg-gray-100 text-gray-800"}`}
                    >
                      {fb.category}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Stars rating={fb.rating} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 max-w-md truncate">{fb.comment}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {new Date(fb.created_at).toLocaleDateString("es-ES")}
                  </td>
                </tr>
              ))}
              {feedbacks.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                    No hay feedback
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
