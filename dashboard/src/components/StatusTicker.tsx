import { useStore } from "../store";

export function StatusTicker() {
  const { satellites, conjunctions, lastRefresh } = useStore();

  const active = satellites.filter(s => s.object_type === "ACTIVE_SATELLITE").length;
  const debris = satellites.filter(s => s.object_type === "DEBRIS").length;
  const rockets = satellites.filter(s => s.object_type === "ROCKET_BODY").length;
  const highRisk = conjunctions.filter(c => c.risk_category === "HIGH" || c.risk_category === "CRITICAL").length;
  const medRisk = conjunctions.filter(c => c.risk_category === "MEDIUM").length;

  const utc = lastRefresh
    ? lastRefresh.toISOString().slice(11, 19)
    : "--:--:--";

  return (
    <div className="ticker-bar area-ticker">
      <span className="ticker-live">LIVE</span>
      <span className="ticker-sep">│</span>

      <span className="ticker-label">Active:</span>
      <span className="ticker-value">{active}</span>
      <span className="ticker-sep">·</span>

      <span className="ticker-label">Debris:</span>
      <span className="ticker-value">{debris}</span>
      <span className="ticker-sep">·</span>

      <span className="ticker-label">Rockets:</span>
      <span className="ticker-value">{rockets}</span>
      <span className="ticker-sep">│</span>

      <span className="ticker-label">HIGH risk:</span>
      <span className="ticker-value-high">{highRisk}</span>
      <span className="ticker-sep">·</span>

      <span className="ticker-label">MED risk:</span>
      <span className="ticker-value-med">{medRisk}</span>

      <span style={{ marginLeft: "auto" }} className="ticker-label">
        UTC: <span className="ticker-value">{utc}</span>
      </span>
    </div>
  );
}
