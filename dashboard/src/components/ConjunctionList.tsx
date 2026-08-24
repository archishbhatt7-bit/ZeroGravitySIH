import { useStore } from "../store";
import { useState, useEffect } from "react";

function TcaCountdown({ tca }: { tca: string }) {
  const [remaining, setRemaining] = useState("");
  const [isPast, setIsPast] = useState(false);

  useEffect(() => {
    const update = () => {
      const now = Date.now();
      const tcaTime = new Date(tca).getTime();
      const diff = tcaTime - now;

      if (diff <= 0) {
        setIsPast(true);
        setRemaining("PASSED");
        return;
      }

      setIsPast(false);
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setRemaining(
        `T-${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`,
      );
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [tca]);

  return (
    <span
      className={`font-mono text-xs tabular-nums ${isPast ? "text-red-500" : "text-emerald-400"}`}
    >
      {remaining}
    </span>
  );
}

export function ConjunctionList() {
  const { conjunctions, setSelectedEvent, selectedEventId, setFocusTarget } =
    useStore();

  const getBadgeColor = (category: string) => {
    switch (category) {
      case "CRITICAL":
        return "bg-red-500/20 text-red-400 border-red-500/50";
      case "HIGH":
        return "bg-orange-500/20 text-orange-400 border-orange-500/50";
      case "MEDIUM":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/50";
      case "LOW":
        return "bg-blue-500/20 text-blue-400 border-blue-500/50";
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/50";
    }
  };

  const handleClick = (c: any) => {
    const id = `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}`;
    setSelectedEvent(id);
    setFocusTarget({ lat: c.lat, lng: c.lng, alt: c.alt });
  };

  return (
    <div className="absolute top-24 left-6 w-[360px] max-h-[calc(100vh-120px)] flex flex-col rounded-xl overflow-hidden glass-panel slide-in-right z-10">
      <h2 className="text-lg font-semibold text-slate-200 mb-4 pb-2 border-b border-white/10 flex items-center justify-between">
        <span>Active Alerts ({conjunctions.length})</span>
        {conjunctions.some((c) => c.risk_category === "CRITICAL") && (
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 glow-critical" />
        )}
      </h2>

      <div className="flex-1 overflow-y-auto pr-2 space-y-3 -mr-2">
        {conjunctions.length === 0 ? (
          <div className="text-center text-slate-500 py-8 text-sm">
            No conjunctions detected within parameters.
          </div>
        ) : (
          conjunctions.map((c, i) => {
            const id = `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}`;
            const isSelected = selectedEventId === id;

            return (
              <div
                key={id + i}
                onClick={() => handleClick(c)}
                className={`p-3 rounded-lg border cursor-pointer transition-all hover-lift ${
                  isSelected
                    ? "bg-slate-800/80 border-cyan-500/50 shadow-[0_0_15px_rgba(0,240,255,0.15)]"
                    : "bg-slate-900/50 border-white/5 hover:border-white/20 hover:bg-slate-800/50"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getBadgeColor(c.risk_category)}`}
                  >
                    {c.risk_category}
                  </span>
                  <TcaCountdown tca={c.tca} />
                </div>

                <div
                  className="text-sm font-semibold truncate text-slate-200"
                  title={c.primary.name}
                >
                  1: {c.primary.name}
                </div>
                <div
                  className="text-sm font-semibold truncate text-slate-200"
                  title={c.secondary.name}
                >
                  2: {c.secondary.name}
                </div>

                <div className="flex justify-between mt-3 text-xs font-mono">
                  <div className="flex flex-col">
                    <span className="text-slate-500">MISS DIST</span>
                    <span className="text-cyan-400">
                      {c.miss_distance_km.toFixed(2)} km
                    </span>
                  </div>
                  <div className="flex flex-col items-center">
                    <span className="text-slate-500">Pc</span>
                    <span className="text-slate-300">
                      {c.collision_probability !== null
                        ? c.collision_probability.toExponential(1)
                        : "—"}
                    </span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-slate-500">SCORE</span>
                    <span className="text-slate-200">
                      {c.risk_score.toFixed(1)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
