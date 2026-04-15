"use client";

import { useState } from "react";
import type { ParsedExercise } from "@/lib/parseTrainingPlan";

interface ExerciseCardProps {
  exercise: ParsedExercise;
  index: number;
  completed?: boolean;
  onToggleComplete?: (exerciseName: string, completed: boolean) => void;
  onNavigateToReport?: () => void;
}

export default function ExerciseCard({
  exercise,
  index,
  completed = false,
  onToggleComplete,
  onNavigateToReport,
}: ExerciseCardProps) {
  const [showVariantes, setShowVariantes] = useState(false);

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {index + 1}. {exercise.name}
          </h3>
          {exercise.objetivo && (
            <span className="inline-block mt-1 text-xs font-medium bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-full">
              {exercise.objetivo}
            </span>
          )}
        </div>
        {exercise.duracion && (
          <span className="flex items-center gap-1 text-sm text-gray-500 bg-gray-100 px-2.5 py-1 rounded-full whitespace-nowrap">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {exercise.duracion}
          </span>
        )}
      </div>

      {/* Organizacion */}
      {exercise.organizacion && (
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs font-medium text-gray-500 uppercase mb-1">Organización</p>
          <p className="text-sm text-gray-700">{exercise.organizacion}</p>
        </div>
      )}

      {/* Descripcion */}
      {exercise.descripcion && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase mb-1">Descripción</p>
          <p className="text-sm text-gray-700 leading-relaxed">{exercise.descripcion}</p>
        </div>
      )}

      {/* Variantes (collapsible) */}
      {exercise.variantes && (
        <div>
          <button
            onClick={() => setShowVariantes(!showVariantes)}
            aria-expanded={showVariantes}
            className="flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
          >
            <svg
              className={`w-4 h-4 transition-transform ${showVariantes ? "rotate-90" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Variantes
          </button>
          {showVariantes && (
            <p className="mt-2 text-sm text-gray-700 pl-5">{exercise.variantes}</p>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="pt-2 border-t flex items-center justify-between">
        {onToggleComplete && (
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={completed}
              onChange={() => onToggleComplete(exercise.name, !completed)}
              className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
            />
            <span className={`text-sm ${completed ? "text-green-700 font-medium" : "text-gray-500"}`}>
              {completed ? "Implementado" : "Marcar como implementado"}
            </span>
          </label>
        )}
        {onNavigateToReport && (
          <button
            onClick={onNavigateToReport}
            className="text-xs text-indigo-600 hover:text-indigo-800 transition-colors"
          >
            Ver en informe táctico →
          </button>
        )}
      </div>
    </div>
  );
}
