import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RFAF Analytics",
  description: "Plataforma de análisis táctico de fútbol con IA",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex">
        {/* Sidebar */}
        <aside className="w-64 bg-indigo-950 text-white flex flex-col fixed h-full">
          <div className="p-6 border-b border-indigo-800">
            <h1 className="text-xl font-bold">⚽ RFAF Analytics</h1>
            <p className="text-xs text-indigo-300 mt-1">Análisis táctico con IA</p>
          </div>
          <nav className="flex-1 p-4 space-y-1">
            <a
              href="/"
              className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-indigo-800 transition-colors text-sm"
            >
              📊 Dashboard
            </a>
            <a
              href="/analyze"
              className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-indigo-800 transition-colors text-sm"
            >
              🎬 Nuevo análisis
            </a>
            <a
              href="/reports"
              className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-indigo-800 transition-colors text-sm"
            >
              📄 Informes
            </a>
            <a
              href="/feedback"
              className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-indigo-800 transition-colors text-sm"
            >
              💬 Feedback
            </a>
          </nav>
          <div className="p-4 border-t border-indigo-800 text-xs text-indigo-400">
            RFAF Analytics v2.0
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 ml-64 bg-gray-50 min-h-screen">{children}</main>
      </body>
    </html>
  );
}
