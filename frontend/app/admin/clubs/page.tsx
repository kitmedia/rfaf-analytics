"use client";

import { useEffect, useState, useCallback } from "react";
import {
  listAdminClubs,
  onboardClub,
  toggleClub,
  updateClub,
  type AdminClubItem,
} from "@/lib/api";

const planOptions = ["BASICO", "PROFESIONAL", "FEDERADO"];
const planColors: Record<string, string> = {
  BASICO: "bg-gray-100 text-gray-800",
  PROFESIONAL: "bg-indigo-100 text-indigo-800",
  FEDERADO: "bg-amber-100 text-amber-800",
};

export default function AdminClubsPage() {
  const [clubs, setClubs] = useState<AdminClubItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<string | null>(null);

  // Onboard form
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPlan, setFormPlan] = useState("BASICO");
  const [formAdminName, setFormAdminName] = useState("");
  const [formAdminPassword, setFormAdminPassword] = useState("");
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");

  const loadClubs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listAdminClubs();
      setClubs(data.clubs);
      setTotal(data.total);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar clubes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadClubs();
  }, [loadClubs]);

  async function handleOnboard(e: React.FormEvent) {
    e.preventDefault();
    setFormLoading(true);
    setFormError("");
    try {
      await onboardClub({
        club_name: formName,
        email: formEmail,
        plan: formPlan,
        admin_name: formAdminName,
        admin_password: formAdminPassword,
      });
      setShowModal(false);
      setFormName("");
      setFormEmail("");
      setFormPlan("BASICO");
      setFormAdminName("");
      setFormAdminPassword("");
      await loadClubs();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Error al crear club");
    } finally {
      setFormLoading(false);
    }
  }

  async function handleToggle(clubId: string) {
    try {
      const result = await toggleClub(clubId);
      setClubs((prev) =>
        prev.map((c) => (c.id === clubId ? { ...c, active: result.active } : c)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cambiar estado");
    }
  }

  async function handlePlanChange(clubId: string, newPlan: string) {
    try {
      const updated = await updateClub(clubId, { plan: newPlan });
      setClubs((prev) => prev.map((c) => (c.id === clubId ? { ...c, plan: updated.plan } : c)));
      setEditingPlan(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al actualizar plan");
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestion de clubes</h1>
          <p className="text-gray-500 text-sm mt-1">{total} clubes registrados</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
        >
          Onboard Club
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 text-left">
            <tr>
              <th className="px-4 py-3 font-medium">Nombre</th>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium">Activo</th>
              <th className="px-4 py-3 font-medium">Usuarios</th>
              <th className="px-4 py-3 font-medium">Analisis</th>
              <th className="px-4 py-3 font-medium">Creado</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {clubs.map((club) => (
              <tr key={club.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{club.name}</td>
                <td className="px-4 py-3 text-gray-600">{club.email}</td>
                <td className="px-4 py-3">
                  {editingPlan === club.id ? (
                    <select
                      value={club.plan}
                      onChange={(e) => handlePlanChange(club.id, e.target.value)}
                      onBlur={() => setEditingPlan(null)}
                      autoFocus
                      className="text-xs border rounded px-2 py-1"
                    >
                      {planOptions.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span
                      onClick={() => setEditingPlan(club.id)}
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium cursor-pointer ${planColors[club.plan] || "bg-gray-100 text-gray-800"}`}
                    >
                      {club.plan}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleToggle(club.id)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${club.active ? "bg-green-500" : "bg-gray-300"}`}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${club.active ? "translate-x-4.5" : "translate-x-1"}`}
                    />
                  </button>
                </td>
                <td className="px-4 py-3 text-gray-600">{club.user_count}</td>
                <td className="px-4 py-3 text-gray-600">
                  {club.analysis_count}
                  <span className="text-gray-400 ml-1">({club.analisis_mes_actual} mes)</span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">
                  {new Date(club.created_at).toLocaleDateString("es-ES")}
                </td>
              </tr>
            ))}
            {clubs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  No hay clubes registrados
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Onboard Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Onboard nuevo club</h2>
            {formError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg mb-4 text-sm">
                {formError}
              </div>
            )}
            <form onSubmit={handleOnboard} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del club
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Plan</label>
                <select
                  value={formPlan}
                  onChange={(e) => setFormPlan(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {planOptions.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del admin
                </label>
                <input
                  type="text"
                  required
                  value={formAdminName}
                  onChange={(e) => setFormAdminName(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password del admin
                </label>
                <input
                  type="password"
                  required
                  value={formAdminPassword}
                  onChange={(e) => setFormAdminPassword(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  {formLoading ? "Creando..." : "Crear club"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
