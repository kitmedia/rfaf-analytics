"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Error al enviar el email");
      }

      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de conexion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 -ml-64">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-indigo-950">RFAF Analytics</h1>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-8">
          {sent ? (
            <div className="text-center">
              <p className="text-2xl mb-2">&#9993;</p>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Revisa tu email</h2>
              <p className="text-gray-500 text-sm">
                Si existe una cuenta con <strong>{email}</strong>, recibiras un enlace para restablecer tu contrasena.
              </p>
              <a
                href="/login"
                className="inline-block mt-6 text-indigo-600 hover:text-indigo-700 text-sm font-medium"
              >
                Volver a iniciar sesion
              </a>
            </div>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Recuperar contrasena</h2>
              <p className="text-gray-500 text-sm mb-6">
                Introduce tu email y te enviaremos un enlace para restablecer tu contrasena.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="entrenador@miclub.es"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
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
                  {loading ? "Enviando..." : "Enviar enlace"}
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-sm text-gray-500 mt-4">
          <a href="/login" className="text-indigo-600 hover:text-indigo-700 font-medium">
            Volver a iniciar sesion
          </a>
        </p>
      </div>
    </div>
  );
}
