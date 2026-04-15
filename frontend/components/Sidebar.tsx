"use client";

import { usePathname } from "next/navigation";
import { getAuth, logout } from "@/lib/auth";
import ThemeToggle from "./ThemeToggle";

export default function Sidebar() {
  const pathname = usePathname();

  // Don't show sidebar on public pages
  const publicPaths = ["/login", "/signup", "/pricing", "/forgot-password", "/reset-password"];
  if (publicPaths.includes(pathname)) return null;

  const auth = getAuth();

  const baseLinks = [
    { href: "/", label: "Dashboard", icon: "📊" },
    { href: "/analyze", label: "Nuevo análisis", icon: "🎬" },
    { href: "/upload", label: "Subir vídeo", icon: "📹" },
    { href: "/reports", label: "Informes", icon: "📄" },
    { href: "/players", label: "Jugadores", icon: "👤" },
    { href: "/rivals", label: "Buscar rival", icon: "🔍" },
    { href: "/feedback", label: "Feedback", icon: "💬" },
    { href: "/settings", label: "Configuración", icon: "⚙️" },
  ];

  const links =
    auth?.role === "admin"
      ? [...baseLinks, { href: "/admin", label: "Admin RFAF", icon: "🛡️" }]
      : baseLinks;

  return (
    <aside className="w-64 bg-indigo-950 text-white flex flex-col fixed h-full">
      <div className="p-6 border-b border-indigo-800">
        <h1 className="text-xl font-bold">RFAF Analytics</h1>
        <p className="text-xs text-indigo-300 mt-1">Análisis táctico con IA</p>
      </div>

      <nav className="flex-1 p-4 space-y-1" aria-label="Navegación principal">
        {links.map((link) => (
          <a
            key={link.href}
            href={link.href}
            aria-current={pathname === link.href ? "page" : undefined}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-sm ${
              pathname === link.href
                ? "bg-indigo-800 text-white"
                : "hover:bg-indigo-800 text-indigo-200"
            }`}
          >
            <span aria-hidden="true">{link.icon}</span> {link.label}
          </a>
        ))}
      </nav>

      <div className="p-4 border-t border-indigo-800">
        {auth ? (
          <div>
            <p className="text-xs text-indigo-300 truncate">{auth.club_name}</p>
            <p className="text-xs text-indigo-400 truncate">{auth.user_name}</p>
            <button
              onClick={logout}
              className="mt-2 text-xs text-indigo-400 hover:text-white transition-colors"
            >
              Cerrar sesión
            </button>
          </div>
        ) : (
          <a href="/login" className="text-xs text-indigo-400 hover:text-white">
            Iniciar sesion
          </a>
        )}
        <div className="mt-2">
          <ThemeToggle />
        </div>
      </div>
    </aside>
  );
}
