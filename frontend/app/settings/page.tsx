"use client";

import { useState } from "react";
import { getAuth, getToken } from "@/lib/auth";
import { changePassword } from "@/lib/api";

export default function SettingsPage() {
  const auth = getAuth();
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");

    if (newPw.length < 8) {
      setError("La nueva contrasena debe tener al menos 8 caracteres.");
      return;
    }
    if (newPw !== confirmPw) {
      setError("Las contrasenas no coinciden.");
      return;
    }

    setLoading(true);
    try {
      const token = getToken();
      if (!token) throw new Error("No autenticado");
      const res = await changePassword(currentPw, newPw, token);
      setMessage(res.message);
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cambiar la contrasena");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Configuracion</h1>
      <p className="text-gray-500 text-sm mt-1">Gestiona tu cuenta y preferencias</p>

      {/* Account info */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mt-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Informacion de cuenta</h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Club</span>
            <span className="font-medium text-gray-900">{auth?.club_name || "-"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Nombre</span>
            <span className="font-medium text-gray-900">{auth?.user_name || "-"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Plan</span>
            <span className="font-medium text-gray-900">{auth?.plan || "-"}</span>
          </div>
        </div>
      </div>

      {/* Change password */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mt-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Cambiar contrasena</h2>

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contrasena actual
            </label>
            <input
              type="password"
              required
              autoComplete="current-password"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
            />
          </div>

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
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar nueva contrasena
            </label>
            <input
              type="password"
              required
              autoComplete="new-password"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          {message && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
              {message}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors font-medium text-sm disabled:opacity-50"
          >
            {loading ? "Guardando..." : "Cambiar contrasena"}
          </button>
        </form>
      </div>

      {/* Billing */}
      <div className="bg-white rounded-xl shadow-sm border p-6 mt-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Facturacion</h2>
        <p className="text-sm text-gray-500 mb-3">
          Gestiona tu suscripcion, metodos de pago y descarga facturas desde el portal de Stripe.
        </p>
        <a
          href="/pricing"
          className="text-indigo-600 hover:text-indigo-700 text-sm font-medium"
        >
          Ver planes y precios &rarr;
        </a>
      </div>
    </div>
  );
}
