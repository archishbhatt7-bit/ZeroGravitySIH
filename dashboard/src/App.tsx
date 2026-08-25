import { useEffect } from "react";
import { useStore } from "./store";
import { GlobeView } from "./components/GlobeView";
import { TopBar } from "./components/TopBar";
import { StatusTicker } from "./components/StatusTicker";
import { StatsCards } from "./components/StatsCards";
import { IntelPanel } from "./components/IntelPanel";
import { GlobeLegend } from "./components/GlobeLegend";
import { LoadingOverlay } from "./components/LoadingOverlay";

function App() {
  const {
    fetchData,
    timeWindowHours,
    distanceThresholdKm,
    filterFormations,
    dataSource,
    staleTleDays,
    autoRefreshInterval,
    setSelectedSatellite,
    setSelectedEvent,
    setFocusTarget,
  } = useStore();

  useEffect(() => {
    fetchData();
  }, [
    timeWindowHours,
    distanceThresholdKm,
    filterFormations,
    dataSource,
    staleTleDays,
    fetchData,
  ]);

  useEffect(() => {
    if (autoRefreshInterval > 0) {
      const interval = setInterval(fetchData, autoRefreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefreshInterval, fetchData]);

  // Global keydown handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedSatellite(null);
        setSelectedEvent(null);
        setFocusTarget(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setSelectedSatellite, setSelectedEvent, setFocusTarget]);

  return (
    <div className="app-grid">
      <LoadingOverlay />

      {/* Row 1: Navbar */}
      <TopBar />

      {/* Row 2: Status Ticker */}
      <StatusTicker />

      {/* Row 3: Stats Cards */}
      <StatsCards />

      {/* Row 4 Left: Globe */}
      <div className="area-globe">
        <GlobeView />
        <GlobeLegend />
      </div>

      {/* Row 4 Right: Intelligence Panel */}
      <IntelPanel />
    </div>
  );
}

export default App;
