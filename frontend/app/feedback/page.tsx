"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEMO_CLUB_ID = "00000000-0000-0000-0000-000000000001";

const CATEGORIES = [
  { value: "usabilidad", label: "Usabilidad", icon: "🖥️" },
  { value: "precision", label: "Precisión del análisis", icon: "🎯" },
  { value: "velocidad", label: "Velocidad", icon: "⚡" },
  { value: "funcionalidad", label: "Funcionalidad nueva", icon: "💡" },
  { value: "otro", label: "Otro", icon: "📝" },
];

export default function FeedbackPage() {
  const [category, setCategory] = useState("");
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!category || !rating) {
      setError("Selecciona una categoría y una puntuación.");
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          club_id: DEMO_CLUB_ID,
          category,
          rating,
          comment: comment || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Error al enviar feedback");
      }

      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="p-8 max-w-lg">
        <div className="bg-green-50 border border-green-200 rounded-xl p-8 text-center">
          <p className="text-4xl mb-4">✅</p>
          <h2 className="text-xl font-bold text-green-800">¡Gracias por tu feedback!</h2>
          <p className="text-green-600 mt-2">
            Tu opinión nos ayuda a mejorar RFAF Analytics.
          </p>
          <a
            href="/"
            className="inline-block mt-6 text-indigo-600 hover:text-indigo-800 font-medium"
          >
            ← Volver al dashboard
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-lg">
      <h1 className="text-2xl font-bold text-gray-900">Enviar feedback</h1>
      <p className="text-gray-500 mt-1">
        Tu opinión como club beta es muy valiosa para mejorar la plataforma.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            ¿Sobre qué quieres opinar? *
          </label>
          <div className="grid grid-cols-2 gap-3">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                type="button"
                onClick={() => setCategory(cat.value)}
                className={`p-3 rounded-lg border text-left text-sm transition-colors ${
                  category === cat.value
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                    : "border-gray-200 hover:border-gray-300 text-gray-700"
                }`}
              >
                <span className="text-lg">{cat.icon}</span>
                <span className="ml-2">{cat.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Rating */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Puntuación *
          </label>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRating(n)}
                className={`w-12 h-12 rounded-lg text-xl transition-colors ${
                  rating >= n
                    ? "bg-amber-400 text-white"
                    : "bg-gray-100 text-gray-400 hover:bg-gray-200"
                }`}
              >
                ★
              </button>
            ))}
          </div>
        </div>

        {/* Comment */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Comentarios
          </label>
          <textarea
            rows={4}
            placeholder="Cuéntanos tu experiencia, sugerencias o problemas..."
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50"
        >
          {loading ? "Enviando..." : "Enviar feedback"}
        </button>
      </form>
    </div>
  );
}
