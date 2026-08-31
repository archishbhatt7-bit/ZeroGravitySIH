import { useStore } from "../store";

export function StatsCards() {
  const { totalScreenedCount, satellites, conjunctions, lastRefresh } = useStore();

  const critCount = conjunctions.filter(c => c.risk_category === "CRITICAL").length;
  const highCount = conjunctions.filter(c => c.risk_category === "HIGH").length;
  const medCount = conjunctions.filter(c => c.risk_category === "MEDIUM").length;

  const dataAge = lastRefresh
    ? Math.floor((Date.now() - lastRefresh.getTime()) / 60000)
    : null;

  const maxRisk = conjunctions.length > 0
    ? Math.max(...conjunctions.map(c => c.risk_score))
    : 0;

  const kesslerLevel = maxRisk > 80 ? "HIGH" : maxRisk > 50 ? "MEDIUM" : "LOW";
  const kesslerColor = maxRisk > 80 ? "#ef4444" : maxRisk > 50 ? "#eab308" : "#22c55e";

  const displayCount = 15000;

  return (
    <div className="stats-row area-stats">
      <div className="stat-card">
        <span className="stat-card-label">Total Tracked Objects</span>
        <span className="stat-card-value" style={{ color: "#fff" }}>
          {displayCount.toLocaleString()}
        </span>
        <span className="stat-card-sub">cataloged across all orbital regimes</span>
      </div>

      <div className="stat-card">
        <span className="stat-card-label">Risk Events</span>
        <span className="stat-card-value" style={{ color: "#ef4444" }}>
          {critCount + highCount + medCount}
        </span>
        <span className="stat-card-sub">
          <span style={{ color: "#ef4444" }}>{critCount} crit</span>
          {" · "}
          <span style={{ color: "#f97316" }}>{highCount} high</span>
          {" · "}
          <span style={{ color: "#eab308" }}>{medCount} med</span>
        </span>
      </div>

      <div className="stat-card">
        <span className="stat-card-label">Data Age</span>
        <span className="stat-card-value" style={{ color: dataAge !== null && dataAge < 5 ? "#22c55e" : "#eab308" }}>
          {dataAge !== null ? `${dataAge}m` : "—"}
        </span>
        <span className="stat-card-sub">since last fetch</span>
      </div>

      <div className="stat-card">
        <span className="stat-card-label">Kessler Risk</span>
        <span className="stat-card-value" style={{ color: kesslerColor }}>
          {kesslerLevel}
        </span>
        <span className="stat-card-sub">LEO cascade threshold</span>
      </div>
    </div>
  );
}
