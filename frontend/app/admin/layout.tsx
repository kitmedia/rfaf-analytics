"use client";

import { usePathname } from "next/navigation";
import { getAuth } from "@/lib/auth";

const tabs = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/clubs", label: "Clubs" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/analyses", label: "Analyses" },
  { href: "/admin/tasks", label: "Tasks" },
  { href: "/admin/operations", label: "Operations" },
  { href: "/admin/feedback-admin", label: "Feedback" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const auth = getAuth();

  if (auth?.role !== "admin") {
    return (
      <div className="p-8 flex items-center justify-center h-screen">
        <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg text-center">
          <h2 className="text-lg font-semibold mb-1">Acceso denegado</h2>
          <p className="text-sm">No tienes permisos de administrador para acceder a esta seccion.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="border-b bg-white sticky top-0 z-10">
        <nav className="flex gap-1 px-6 pt-2 overflow-x-auto">
          {tabs.map((tab) => {
            const isActive =
              tab.href === "/admin"
                ? pathname === "/admin"
                : pathname.startsWith(tab.href);
            return (
              <a
                key={tab.href}
                href={tab.href}
                className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors whitespace-nowrap ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700 border border-b-0 border-indigo-200"
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                }`}
              >
                {tab.label}
              </a>
            );
          })}
        </nav>
      </div>
      {children}
    </div>
  );
}
