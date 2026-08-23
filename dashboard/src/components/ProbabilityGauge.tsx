import { useMemo } from 'react';

interface ProbabilityGaugeProps {
  value: number | null;
  method: string | null;
}

export function ProbabilityGauge({ value, method }: ProbabilityGaugeProps) {
  const { normalizedAngle, color, formattedValue, riskLabel } = useMemo(() => {
    if (value === null || value === undefined) {
      return { normalizedAngle: 0, color: '#6b7280', formattedValue: 'N/A', riskLabel: 'Unknown' };
    }

    // Map log10(Pc) to a 0-1 scale for the gauge
    // Range: 1e-10 (negligible) → 1e-2 (certain collision)
    const logVal = Math.log10(Math.max(value, 1e-12));
    const minLog = -10;
    const maxLog = -2;
    const normalized = Math.max(0, Math.min(1, (logVal - minLog) / (maxLog - minLog)));

    let gaugeColor = '#22c55e'; // green
    let label = 'Negligible';
    if (value > 1e-4) {
      gaugeColor = '#ef4444'; // red
      label = 'High Risk';
    } else if (value > 1e-6) {
      gaugeColor = '#eab308'; // yellow
      label = 'Elevated';
    } else if (value > 1e-8) {
      gaugeColor = '#3b82f6'; // blue
      label = 'Low';
    }

    const formatted = value < 1e-10 ? '< 1e-10' : value.toExponential(2);

    return {
      normalizedAngle: normalized * 240, // 240 degrees for the arc
      color: gaugeColor,
      formattedValue: formatted,
      riskLabel: label,
    };
  }, [value]);

  // SVG arc gauge
  const size = 120;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const center = size / 2;

  // Arc starts at 150° and ends at 390° (240° sweep)
  const startAngle = 150;
  const endAngle = startAngle + normalizedAngle;

  const polarToCartesian = (cx: number, cy: number, r: number, angleDeg: number) => {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  const describeArc = (cx: number, cy: number, r: number, startDeg: number, endDeg: number) => {
    const start = polarToCartesian(cx, cy, r, endDeg);
    const end = polarToCartesian(cx, cy, r, startDeg);
    const largeArcFlag = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
  };

  return (
    <div className="bg-slate-900/50 p-4 rounded-lg border border-white/5 flex flex-col items-center">
      <div className="text-[10px] text-slate-500 font-semibold mb-2 w-full">COLLISION PROBABILITY (Pc)</div>
      
      <div className="relative" style={{ width: size, height: size * 0.7 }}>
        <svg width={size} height={size * 0.7} viewBox={`0 0 ${size} ${size * 0.75}`}>
          {/* Background arc */}
          <path
            d={describeArc(center, center, radius, 150, 390)}
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Value arc */}
          {normalizedAngle > 0 && (
            <path
              d={describeArc(center, center, radius, startAngle, endAngle)}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
              style={{ filter: `drop-shadow(0 0 6px ${color}60)` }}
            />
          )}
        </svg>

        {/* Center value */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
          <div className="font-mono text-base font-bold" style={{ color }}>{formattedValue}</div>
          <div className="text-[9px] text-slate-500 mt-0.5">{riskLabel}</div>
        </div>
      </div>

      {method && (
        <div className="text-[9px] text-slate-600 mt-1 font-mono">
          Method: {method.replace(/_/g, ' ')}
        </div>
      )}
    </div>
  );
}
