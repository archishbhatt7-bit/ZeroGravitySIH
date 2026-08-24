import { useStore } from "../store";
import { SlidersHorizontal } from "lucide-react";

export function ControlPanel() {
  const {
    timeWindowHours,
    setTimeWindow,
    distanceThresholdKm,
    setDistanceThreshold,
    filterFormations,
    setFilterFormations,
  } = useStore();

  return (
    <div className="absolute bottom-6 left-6 glass-panel w-80 p-5 !h-auto">
      <div className="flex items-center gap-2 mb-4">
        <SlidersHorizontal className="w-5 h-5 text-cyan-400" />
        <h2 className="text-lg font-semibold text-slate-200">
          Screening Parameters
        </h2>
      </div>

      <div className="space-y-5">
        <div>
          <div className="flex justify-between mb-1">
            <label className="text-xs text-slate-400">Time Window</label>
            <span className="text-xs font-mono text-cyan-400">
              {timeWindowHours}h
            </span>
          </div>
          <input
            type="range"
            min="6"
            max="72"
            step="6"
            value={timeWindowHours}
            onChange={(e) => setTimeWindow(Number(e.target.value))}
            className="w-full accent-cyan-500 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>6h</span>
            <span>24h</span>
            <span>72h</span>
          </div>
        </div>

        <div>
          <div className="flex justify-between mb-1">
            <label className="text-xs text-slate-400">
              Miss Distance Threshold
            </label>
            <span className="text-xs font-mono text-cyan-400">
              {distanceThresholdKm} km
            </span>
          </div>
          <input
            type="range"
            min="1"
            max="50"
            step="1"
            value={distanceThresholdKm}
            onChange={(e) => setDistanceThreshold(Number(e.target.value))}
            className="w-full accent-cyan-500 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-white/10">
          <label className="text-sm text-slate-300">
            Filter Formations (ISS/CSS)
          </label>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={filterFormations}
              onChange={(e) => setFilterFormations(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-500"></div>
          </label>
        </div>
      </div>
    </div>
  );
}
