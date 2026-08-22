import type { RiskFactors } from '../types';

interface RiskBreakdownChartProps {
  factors: RiskFactors;
}

export function RiskBreakdownChart({ factors }: RiskBreakdownChartProps) {
  // Normalize factors for display
  const maxBarWidth = 100;
  
  const renderBar = (label: string, value: number, max: number, colorClass: string) => {
    const width = Math.min(100, (value / max) * 100);
    return (
      <div className="mb-2">
        <div className="flex justify-between text-[10px] text-slate-400 mb-1">
          <span>{label}</span>
          <span className="font-mono">{value.toFixed(2)}</span>
        </div>
        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={`h-full ${colorClass} transition-all duration-500`} 
            style={{ width: `${width}%` }} 
          />
        </div>
      </div>
    );
  };

  return (
    <div className="bg-slate-900/50 p-3 rounded-lg border border-white/5">
      <div className="text-[10px] text-slate-500 mb-3 font-semibold">RISK FACTORS</div>
      {renderBar("Distance Score", factors.distance_score, 100, "bg-red-500")}
      {renderBar("Velocity Score", factors.velocity_score, 100, "bg-orange-500")}
      {renderBar("Size Multiplier", factors.size_multiplier, 2.0, "bg-blue-500")}
      {renderBar("Maneuver Multiplier", factors.maneuver_multiplier, 1.5, "bg-purple-500")}
      {renderBar("Urgency Multiplier", factors.urgency_multiplier, 2.0, "bg-yellow-500")}
    </div>
  );
}
