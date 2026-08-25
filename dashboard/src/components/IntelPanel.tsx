import { useState } from "react";
import { useStore } from "../store";
import { format } from "date-fns";

const HISTORICAL_EVENTS = [
  { name: "Fengyun-1C ASAT Test", date: "Jan 11, 2007", count: "3,500+", color: "#ef4444" },
  { name: "Iridium 33 / Cosmos 2251", date: "Feb 10, 2009", count: "2,300+", color: "#f97316" },
  { name: "Cosmos 1408 ASAT Test", date: "Nov 15, 2021", count: "1,500+", color: "#ef4444" },
  { name: "Starlink Megaconstellation", date: "2019–present", count: "42,000", color: "#eab308" },
  { name: "Kessler Syndrome", date: "1978 — Kessler & Cour-Palais", count: "APPROACHING", color: "#ef4444" },
];

type Tab = "DATA" | "CONJUNCTIONS" | "SETTINGS";

export function IntelPanel() {
  const [activeTab, setActiveTab] = useState<Tab>("DATA");
  const {
    conjunctions,
    setSelectedEvent,
    selectedEventId,
    setFocusTarget,
    timeWindowHours,
    distanceThresholdKm,
    filterFormations,
    setTimeWindow,
    setDistanceThreshold,
    setFilterFormations,
    layerVisibility,
    setLayerVisibility,
  } = useStore();

  const highCount = conjunctions.filter(c => c.risk_category === "HIGH" || c.risk_category === "CRITICAL").length;
  const medCount = conjunctions.filter(c => c.risk_category === "MEDIUM").length;

  const handleConjClick = (c: typeof conjunctions[0]) => {
    const eventId = `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}`;
    setSelectedEvent(eventId);
    setFocusTarget({ lat: c.lat, lng: c.lng, alt: c.alt });
  };

  const riskColor = (cat: string) => {
    switch (cat) {
      case "CRITICAL": return "#ef4444";
      case "HIGH": return "#f97316";
      case "MEDIUM": return "#eab308";
      default: return "#3b82f6";
    }
  };

  return (
    <div className="intel-panel area-intel">
      {/* Tab Bar */}
      <div className="intel-tabs">
        {(["DATA", "CONJUNCTIONS", "SETTINGS"] as Tab[]).map((tab) => (
          <button
            key={tab}
            className={`intel-tab ${activeTab === tab ? "intel-tab-active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="intel-content">
        {activeTab === "DATA" && (
          <>
            {/* Historical Events */}
            <div className="intel-section">
              <div className="intel-section-header">
                <span>Historical Events</span>
                <span style={{ color: "#555", fontSize: "9px", letterSpacing: 0 }}>Click to explore</span>
              </div>
              {HISTORICAL_EVENTS.map((ev) => (
                <div key={ev.name} className="hist-event">
                  <span className="hist-dot" style={{ background: ev.color }} />
                  <div className="hist-info">
                    <div className="hist-name">{ev.name}</div>
                    <div className="hist-date">{ev.date}</div>
                  </div>
                  <div className="hist-count">{ev.count}</div>
                </div>
              ))}
            </div>

            {/* Quick Conjunctions Preview */}
            <div className="intel-section">
              <div className="intel-section-header">
                <span>Conjunctions</span>
                <span className="intel-section-badge" style={{ color: "#f97316", background: "rgba(249, 115, 22, 0.1)" }}>
                  {highCount} HIGH · {medCount} MED
                </span>
              </div>
              {conjunctions.slice(0, 5).map((c, i) => (
                <div key={i} className="conj-card" onClick={() => handleConjClick(c)}>
                  <span
                    className="conj-risk-badge"
                    style={{
                      color: riskColor(c.risk_category),
                      background: `${riskColor(c.risk_category)}15`,
                      border: `1px solid ${riskColor(c.risk_category)}30`,
                    }}
                  >
                    {c.risk_category.slice(0, 3)}
                  </span>
                  <div className="conj-info">
                    <div className="conj-name">{c.primary.name}</div>
                    <div className="conj-meta">
                      vs {c.secondary.name} · TCA {format(new Date(c.tca), "HH:mm")}
                    </div>
                  </div>
                  <div className="conj-distance" style={{ color: riskColor(c.risk_category) }}>
                    {c.miss_distance_km.toFixed(2)}
                    <span className="conj-distance-unit">km</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {activeTab === "CONJUNCTIONS" && (
          <div className="intel-section">
            <div className="intel-section-header">
              <span>All Conjunctions ({conjunctions.length})</span>
            </div>
            {conjunctions.map((c, i) => {
              const eventId = `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}`;
              const isSelected = eventId === selectedEventId;

              return (
                <div key={i}>
                  <div
                    className="conj-card"
                    onClick={() => handleConjClick(c)}
                    style={isSelected ? { background: "rgba(255, 150, 0, 0.05)" } : {}}
                  >
                    <span
                      className="conj-risk-badge"
                      style={{
                        color: riskColor(c.risk_category),
                        background: `${riskColor(c.risk_category)}15`,
                        border: `1px solid ${riskColor(c.risk_category)}30`,
                      }}
                    >
                      {c.risk_category.slice(0, 3)}
                    </span>
                    <div className="conj-info">
                      <div className="conj-name">{c.primary.name}</div>
                      <div className="conj-meta">
                        vs {c.secondary.name} · P={c.collision_probability !== null ? c.collision_probability.toExponential(2) : "N/A"} · TCA {format(new Date(c.tca), "MMM dd HH:mm")}
                      </div>
                    </div>
                    <div className="conj-distance" style={{ color: riskColor(c.risk_category) }}>
                      {c.miss_distance_km.toFixed(2)}
                      <span className="conj-distance-unit">km</span>
                    </div>
                  </div>

                  {isSelected && (
                    <div style={{ padding: "8px 14px 12px", background: "rgba(255,255,255,0.01)", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                      <div style={{ fontSize: "10px", color: "#888", fontFamily: "JetBrains Mono, monospace", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                        <div>Rel. Velocity: <span style={{ color: "#ddd" }}>{c.relative_velocity_km_s.toFixed(2)} km/s</span></div>
                        <div>Risk Score: <span style={{ color: riskColor(c.risk_category) }}>{c.risk_score.toFixed(1)}</span></div>
                        <div>Altitude: <span style={{ color: "#ddd" }}>{c.alt.toFixed(0)} km</span></div>
                        <div>Confidence: <span style={{ color: c.confidence === "NORMAL" ? "#22c55e" : "#eab308" }}>{c.confidence}</span></div>
                      </div>
                      <div style={{ fontSize: "9px", color: "#666", marginTop: "6px", fontStyle: "italic" }}>
                        {c.recommendation}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "SETTINGS" && (
          <div style={{ padding: "14px" }}>
            <div style={{ marginBottom: "16px" }}>
              <div className="stat-card-label" style={{ marginBottom: "6px" }}>Time Window</div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <input
                  type="range"
                  min={1}
                  max={72}
                  value={timeWindowHours}
                  onChange={(e) => setTimeWindow(Number(e.target.value))}
                  style={{ flex: 1, accentColor: "#ff9500" }}
                />
                <span className="font-mono" style={{ fontSize: "12px", color: "#ff9500", width: "36px", textAlign: "right" }}>{timeWindowHours}h</span>
              </div>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <div className="stat-card-label" style={{ marginBottom: "6px" }}>Miss Distance Threshold</div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <input
                  type="range"
                  min={1}
                  max={100}
                  value={distanceThresholdKm}
                  onChange={(e) => setDistanceThreshold(Number(e.target.value))}
                  style={{ flex: 1, accentColor: "#ff9500" }}
                />
                <span className="font-mono" style={{ fontSize: "12px", color: "#ff9500", width: "46px", textAlign: "right" }}>{distanceThresholdKm} km</span>
              </div>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={filterFormations}
                  onChange={(e) => setFilterFormations(e.target.checked)}
                  style={{ accentColor: "#ff9500" }}
                />
                <span style={{ fontSize: "11px", color: "#999" }}>Filter Formations (ISS/CSS)</span>
              </label>
            </div>

            <div className="stat-card-label" style={{ marginBottom: "8px", marginTop: "20px" }}>Layer Visibility</div>
            {([
              ["activeSatellites", "Active Satellites"],
              ["debris", "Debris"],
              ["rocketBodies", "Rocket Bodies"],
              ["unknown", "Unknown"],
              ["orbitPaths", "Orbit Paths"],
              ["conjunctionHighlights", "Conjunctions"],
            ] as const).map(([key, label]) => (
              <label key={key} style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={layerVisibility[key]}
                  onChange={(e) => setLayerVisibility(key, e.target.checked)}
                  style={{ accentColor: "#ff9500" }}
                />
                <span style={{ fontSize: "11px", color: "#999" }}>{label}</span>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
