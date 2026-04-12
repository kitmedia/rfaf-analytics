"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("La contrasena debe tener al menos 8 caracteres.");
      return;
    }
    if (password !== confirm) {
      setError("Las contrasenas no coinciden.");
      return;
    }
    if (!token) {
      setError("Enlace de recuperacion invalido. Solicita uno nuevo.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Error al restablecer la contrasena");
      }

      setDone(true);
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
          {done ? (
            <div className="text-center">
              <p className="text-2xl mb-2">&#10003;</p>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Contrasena actualizada</h2>
              <p className="text-gray-500 text-sm">Ya puedes iniciar sesion con tu nueva contrasena.</p>
              <a
                href="/login"
                className="inline-block mt-6 bg-indigo-600 text-white px-6 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
              >
                Iniciar sesion
              </a>
            </div>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Nueva contrasena</h2>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nueva contrasena
                  </label>
                  <input
                    type="password"
                    required
                    autoComplete="new-password"
                    placeholder="Minimo 8 caracteres"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confirmar contrasena
                  </label>
                  <input
                    type="password"
                    required
                    autoComplete="new-password"
                    placeholder="Repite la contrasena"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
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
                  {loading ? "Guardando..." : "Guardar contrasena"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
