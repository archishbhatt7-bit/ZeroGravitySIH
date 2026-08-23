import { useEffect } from 'react';
import { useStore } from './store';
import { GlobeView } from './components/GlobeView';
import { TopBar } from './components/TopBar';
import { ControlPanel } from './components/ControlPanel';
import { ConjunctionList } from './components/ConjunctionList';
import { EventDetail } from './components/EventDetail';
import { ObjectInfoPanel } from './components/ObjectInfoPanel';
import { LoadingOverlay } from './components/LoadingOverlay';
import { SearchBar } from './components/SearchBar';
import { LayerToggles } from './components/LayerToggles';

function App() {
  const { 
    fetchData, timeWindowHours, distanceThresholdKm, filterFormations, 
    dataSource, staleTleDays, autoRefreshInterval, 
    setSelectedSatellite, setSelectedEvent, setFocusTarget,
    isAnalysisMode, setAnalysisMode
  } = useStore();

  useEffect(() => {
    fetchData();
  }, [timeWindowHours, distanceThresholdKm, filterFormations, dataSource, staleTleDays, fetchData]);

  useEffect(() => {
    if (autoRefreshInterval > 0) {
      const interval = setInterval(fetchData, autoRefreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefreshInterval, fetchData]);

  // Global keydown handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedSatellite(null);
        setSelectedEvent(null);
        setFocusTarget(null);
        setAnalysisMode(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setSelectedSatellite, setSelectedEvent, setFocusTarget, setAnalysisMode]);

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#05060a] text-white font-sans">
      <LoadingOverlay />
      
      {/* 3D Background */}
      <GlobeView />

      {/* UI Overlay */}
      <TopBar />
      
      {!isAnalysisMode && <SearchBar />}
      {!isAnalysisMode && <ControlPanel />}
      {!isAnalysisMode && <LayerToggles />}
      
      {isAnalysisMode && <ConjunctionList />}
      {isAnalysisMode && <EventDetail />}
      
      {!isAnalysisMode && <ObjectInfoPanel />}

      {/* Analyze Toggle Button */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex gap-4">
        {!isAnalysisMode ? (
          <button 
            onClick={() => setAnalysisMode(true)}
            className="px-8 py-3 bg-red-500/20 text-red-400 border border-red-500/50 rounded-full font-bold shadow-[0_0_20px_rgba(239,68,68,0.2)] hover:bg-red-500/30 hover:shadow-[0_0_30px_rgba(239,68,68,0.4)] transition-all hover-lift"
          >
            ANALYZE CONJUNCTIONS
          </button>
        ) : (
          <button 
            onClick={() => setAnalysisMode(false)}
            className="px-6 py-2 bg-slate-800/50 text-slate-300 border border-white/10 rounded-full font-semibold hover:bg-slate-700/50 transition-all hover-lift text-sm"
          >
            EXIT ANALYSIS
          </button>
        )}
      </div>
    </div>
  );
}

export default App;
