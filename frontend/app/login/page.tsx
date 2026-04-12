"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de autenticación");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 -ml-64">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-indigo-950">RFAF Analytics</h1>
          <p className="text-gray-500 mt-2">Análisis táctico con IA</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Iniciar sesión</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña
              </label>
              <input
                type="password"
                required
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>

          <p className="text-right mt-3">
            <a href="/forgot-password" className="text-xs text-indigo-600 hover:text-indigo-700">
              Has olvidado tu contrasena?
            </a>
          </p>
        </div>

        <p className="text-center text-sm text-gray-500 mt-4">
          No tienes cuenta?{" "}
          <a href="/signup" className="text-indigo-600 hover:text-indigo-700 font-medium">
            Registrate
          </a>
        </p>

        <p className="text-center text-xs text-gray-400 mt-4">
          RFAF Analytics Platform v2.0 &middot; Real Federacion Aragonesa de Futbol
        </p>
      </div>
    </div>
  );
}
