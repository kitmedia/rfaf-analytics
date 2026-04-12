"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("rfaf_theme");
    if (stored === "dark") {
      setDark(true);
      document.documentElement.classList.add("dark");
    }
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    if (next) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("rfaf_theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("rfaf_theme", "light");
    }
  }

  return (
    <button
      onClick={toggle}
      className="text-xs text-indigo-400 hover:text-white transition-colors"
      title={dark ? "Modo claro" : "Modo oscuro"}
    >
      {dark ? "\u2600\uFE0F Modo claro" : "\u263E Modo oscuro"}
    </button>
  );
}
