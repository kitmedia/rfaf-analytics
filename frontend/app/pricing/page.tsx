"use client";

import { getClubId } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const plans = [
  {
    name: "Basico",
    price: 49,
    value: "BASICO",
    features: [
      "3 analisis de partido/mes",
      "Informe tactico 12 secciones",
      "PDF con branding RFAF",
      "Metricas xG, PPDA, Field Tilt",
      "Graficas mplsoccer",
      "Email automatico al completar",
    ],
    cta: "Empezar",
    popular: false,
  },
  {
    name: "Profesional",
    price: 149,
    value: "PROFESIONAL",
    features: [
      "Analisis ilimitados",
      "Todo lo del plan Basico",
      "Chatbot tactico con IA",
      "Comparativa con rivales",
      "Soporte prioritario",
      "Panel de metricas avanzado",
    ],
    cta: "Suscribirse",
    popular: true,
  },
  {
    name: "Federado",
    price: 104,
    originalPrice: 149,
    value: "FEDERADO",
    features: [
      "Analisis ilimitados",
      "Todo lo del plan Profesional",
      "-30% exclusivo RFAF",
      "Onboarding personalizado",
      "Acceso anticipado a nuevas funciones",
      "Soporte dedicado",
    ],
    cta: "Solicitar acceso",
    popular: false,
    badge: "-30% RFAF",
  },
];

async function handleCheckout(planValue: string) {
  const clubId = getClubId();
  if (!clubId) {
    window.location.href = "/signup";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/clubs/${clubId}/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan: planValue }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Error al iniciar el pago");
      return;
    }

    const data = await res.json();
    window.location.href = data.checkout_url;
  } catch {
    alert("Error de conexion. Intenta de nuevo.");
  }
}

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-gray-50 -ml-64">
      <div className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-gray-900">
            Planes RFAF Analytics
          </h1>
          <p className="text-gray-500 mt-3 max-w-xl mx-auto">
            Analisis tactico con IA para clubes de la Real Federacion Aragonesa de Futbol.
            Elige el plan que mejor se adapte a tu club.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.value}
              className={`bg-white rounded-2xl border-2 p-8 flex flex-col relative ${
                plan.popular
                  ? "border-indigo-600 shadow-lg"
                  : "border-gray-200 shadow-sm"
              }`}
            >
              {plan.popular && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                  Mas popular
                </span>
              )}
              {plan.badge && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
                  {plan.badge}
                </span>
              )}

              <h2 className="text-lg font-semibold text-gray-900">{plan.name}</h2>

              <div className="mt-4 flex items-baseline gap-1">
                {plan.originalPrice && (
                  <span className="text-lg text-gray-400 line-through">
                    {plan.originalPrice} EUR
                  </span>
                )}
                <span className="text-4xl font-bold text-gray-900">
                  {plan.price}
                </span>
                <span className="text-gray-500 text-sm">EUR/mes</span>
              </div>

              <ul className="mt-6 space-y-3 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="text-indigo-600 mt-0.5">&#10003;</span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleCheckout(plan.value)}
                className={`mt-8 w-full py-3 rounded-lg font-medium transition-colors text-sm ${
                  plan.popular
                    ? "bg-indigo-600 text-white hover:bg-indigo-700"
                    : "bg-gray-100 text-gray-900 hover:bg-gray-200"
                }`}
              >
                {plan.cta}
              </button>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-gray-400 mt-10">
          Todos los precios con IVA incluido. Cancela cuando quieras desde el portal de facturacion.
        </p>
      </div>
    </div>
  );
}
