import { Search, RefreshCw, Star, Sun } from "lucide-react";
import { useStore } from "../store";
import { useState, useEffect, useRef } from "react";

export function TopBar() {
  const { fetchData, loading, searchSatellites, setSelectedSatellite, setFocusTarget, satellites } = useStore();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<typeof satellites>([]);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const q = query.toLowerCase();
    const matched = satellites
      .filter(s => s.name.toLowerCase().includes(q) || String(s.norad_id).includes(q))
      .slice(0, 8);
    setResults(matched);
  }, [query, satellites]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="navbar area-navbar">
      <div className="navbar-logo">
        <span style={{ fontSize: "16px" }}>🛰️</span>
        <h1>ZeroGravity</h1>
        <span className="navbar-badge">ORBITAL INTELLIGENCE</span>
      </div>

      <div className="navbar-search" ref={searchRef} style={{ position: "relative" }}>
        <Search size={12} color="#555" />
        <input
          placeholder="Search by name or NORAD ID..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setShowResults(true); }}
          onFocus={() => setShowResults(true)}
        />
        {showResults && results.length > 0 && (
          <div style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            background: "#0c0d12",
            border: "1px solid rgba(255,255,255,0.08)",
            borderTop: "none",
            borderRadius: "0 0 4px 4px",
            zIndex: 100,
            maxHeight: "240px",
            overflowY: "auto",
          }}>
            {results.map((s) => (
              <div
                key={s.norad_id}
                onClick={() => {
                  setSelectedSatellite(s.norad_id);
                  setQuery(s.name);
                  setShowResults(false);
                }}
                style={{
                  padding: "6px 10px",
                  fontSize: "11px",
                  color: "#ccc",
                  cursor: "pointer",
                  borderBottom: "1px solid rgba(255,255,255,0.03)",
                  fontFamily: "JetBrains Mono, monospace",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,150,0,0.05)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <span style={{ color: "#ff9500" }}>{s.norad_id}</span>
                {" — "}
                {s.name}
                <span style={{ color: "#555", marginLeft: "8px", fontSize: "9px" }}>{s.object_type}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="navbar-actions">
        <button className="navbar-btn" title="Theme"><Sun size={13} /></button>
        <button className="navbar-btn" title="Favorites"><Star size={13} /></button>
        <button
          className="navbar-btn navbar-btn-primary"
          onClick={() => fetchData()}
          disabled={loading}
          title="Refresh data"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          REFRESH
        </button>
      </div>
    </div>
  );
}
