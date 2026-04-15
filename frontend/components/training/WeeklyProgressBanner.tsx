"use client";

interface WeeklyProgressBannerProps {
  completedCount: number;
  totalCount: number;
}

export default function WeeklyProgressBanner({
  completedCount,
  totalCount,
}: WeeklyProgressBannerProps) {
  if (totalCount === 0) return null;

  const pct = Math.round((completedCount / totalCount) * 100);

  return (
    <div className="bg-green-50 rounded-xl border border-green-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-green-900">
          Esta semana: {completedCount} de {totalCount} ejercicios implementados
        </p>
        <span className="text-sm font-bold text-green-700">{pct}%</span>
      </div>
      <div className="w-full bg-green-200 rounded-full h-2.5">
        <div
          className="bg-green-600 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
