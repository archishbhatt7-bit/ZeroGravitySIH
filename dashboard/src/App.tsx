import { useEffect } from 'react';
import { useStore } from './store';
import { GlobeView } from './components/GlobeView';
import { TopBar } from './components/TopBar';
import { ControlPanel } from './components/ControlPanel';
import { ConjunctionList } from './components/ConjunctionList';
import { EventDetail } from './components/EventDetail';
import { ObjectInfoPanel } from './components/ObjectInfoPanel';
import { LoadingOverlay } from './components/LoadingOverlay';

function App() {
  const { fetchData, timeWindowHours, distanceThresholdKm, filterFormations, dataSource, staleTleDays, autoRefreshInterval } = useStore();

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
        useStore.getState().setSelectedSatellite(null);
        useStore.getState().setSelectedEvent(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#05060a] text-white font-sans">
      <LoadingOverlay />
      
      {/* 3D Background */}
      <GlobeView />

      {/* UI Overlay */}
      <TopBar />
      <ControlPanel />
      <ConjunctionList />
      <EventDetail />
      <ObjectInfoPanel />
    </div>
  );
}

export default App;
