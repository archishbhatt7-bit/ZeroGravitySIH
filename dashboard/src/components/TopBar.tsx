import { RefreshCw, AlertTriangle, Activity, WifiOff } from "lucide-react";
import { useStore } from "../store";
import { format } from "date-fns";

export function TopBar() {
  const { satellites, conjunctions, lastRefresh, fetchData, loading, error } =
    useStore();

  const criticalCount = conjunctions.filter(
    (c) => c.risk_category === "CRITICAL",
  ).length;
  const highCount = conjunctions.filter(
    (c) => c.risk_category === "HIGH",
  ).length;

  const highestScore =
    conjunctions.length > 0
      ? Math.max(...conjunctions.map((c) => c.risk_score))
      : 0;

  return (
    <>
      <div className="absolute top-0 left-0 w-full h-16 bg-slate-900/80 backdrop-blur-md border-b border-white/10 z-20 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Activity className="text-cyan-400 w-6 h-6" />
          <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            ZeroGravity
          </h1>
          <span className="text-[10px] font-mono text-slate-600 bg-slate-800/50 px-2 py-0.5 rounded-full border border-white/5">
            DASHBOARD
          </span>
        </div>

        <div className="flex items-center gap-8">
          <div className="flex flex-col">
            <span className="text-xs text-slate-400 uppercase">
              Tracked Objects
            </span>
            <span className="text-lg font-mono tabular-nums">
              {satellites.length.toLocaleString()}
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-xs text-slate-400 uppercase">
              Active Alerts (Crit/High)
            </span>
            <span className="text-lg font-mono flex items-center gap-2">
              {criticalCount + highCount > 0 && (
                <AlertTriangle className="w-4 h-4 text-red-500" />
              )}
              <span className="text-red-400">{criticalCount}</span> /{" "}
              <span className="text-orange-400">{highCount}</span>
            </span>
          </div>

          <div className="flex flex-col">
            <span className="text-xs text-slate-400 uppercase">
              Max Risk Score
            </span>
            <span
              className={`text-lg font-mono tabular-nums ${highestScore > 80 ? "text-red-500" : highestScore > 60 ? "text-orange-500" : "text-yellow-500"}`}
            >
              {highestScore.toFixed(1)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right flex flex-col">
            <span className="text-xs text-slate-400">Last Refresh</span>
            <span className="text-sm font-mono text-slate-200 tabular-nums">
              {lastRefresh ? format(lastRefresh, "HH:mm:ss") : "--:--:--"}
            </span>
          </div>

          <button
            onClick={() => fetchData()}
            disabled={loading}
            className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-all border border-cyan-500/30 disabled:opacity-50 hover-lift"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="absolute top-16 left-0 w-full z-20 bg-red-900/80 backdrop-blur-md border-b border-red-500/30 px-6 py-3 flex items-center justify-between slide-in-down">
          <div className="flex items-center gap-3">
            <WifiOff className="w-5 h-5 text-red-400" />
            <div>
              <div className="text-sm font-semibold text-red-300">
                Connection Error
              </div>
              <div className="text-xs text-red-400/80">{error}</div>
            </div>
          </div>
          <button
            onClick={() => fetchData()}
            disabled={loading}
            className="px-4 py-1.5 bg-red-500/20 text-red-300 border border-red-500/40 rounded-lg text-xs font-semibold hover:bg-red-500/30 transition-all disabled:opacity-50"
          >
            {loading ? "Retrying..." : "Retry"}
          </button>
        </div>
      )}
    </>
  );
}
