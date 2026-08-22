import { create } from 'zustand';
import type { Satellite, ConjunctionEvent, LayerVisibility } from './types';

interface DashboardState {
  satellites: Satellite[];
  conjunctions: ConjunctionEvent[];
  loading: boolean;
  error: string | null;
  lastRefresh: Date | null;
  
  // Selection state
  selectedSatelliteId: number | null;
  selectedEventId: string | null;
  
  // Filter state
  timeWindowHours: number;
  distanceThresholdKm: number;
  filterFormations: boolean;
  autoRefreshInterval: number; // 0 = off, otherwise ms
  dataSource: string;
  staleTleDays: number;
  
  layerVisibility: LayerVisibility;
  
  // Actions
  fetchData: () => Promise<void>;
  setSelectedSatellite: (id: number | null) => void;
  setSelectedEvent: (id: string | null) => void;
  setTimeWindow: (hours: number) => void;
  setDistanceThreshold: (km: number) => void;
  setFilterFormations: (filter: boolean) => void;
  setAutoRefreshInterval: (ms: number) => void;
  setDataSource: (source: string) => void;
  setStaleTleDays: (days: number) => void;
  setLayerVisibility: (layer: keyof LayerVisibility, visible: boolean) => void;
}

const API_BASE = 'http://localhost:8000/api';

export const useStore = create<DashboardState>((set, get) => ({
  satellites: [],
  conjunctions: [],
  loading: false,
  error: null,
  lastRefresh: null,
  
  selectedSatelliteId: null,
  selectedEventId: null,
  
  timeWindowHours: 24,
  distanceThresholdKm: 10,
  filterFormations: true,
  autoRefreshInterval: 0,
  dataSource: 'celestrak_active',
  staleTleDays: 3,
  
  layerVisibility: {
    activeSatellites: true,
    debris: true,
    rocketBodies: true,
    unknown: true,
    orbitPaths: true,
    conjunctionHighlights: true,
  },
  
  fetchData: async () => {
    set({ loading: true, error: null });
    try {
      const state = get();
      
      const [satRes, conjRes] = await Promise.all([
        fetch(`${API_BASE}/satellites?data_source=${state.dataSource}&max_objects=1500`),
        fetch(`${API_BASE}/conjunctions?hours=${state.timeWindowHours}&threshold_km=${state.distanceThresholdKm}&filter_formations=${state.filterFormations}&data_source=${state.dataSource}&max_objects=1500&stale_tle_days=${state.staleTleDays}`)
      ]);
      
      if (!satRes.ok || !conjRes.ok) throw new Error("Failed to fetch data");
      
      const satData = await satRes.json();
      const conjData = await conjRes.json();
      
      set({ 
        satellites: satData.satellites, 
        conjunctions: conjData.conjunctions,
        loading: false,
        lastRefresh: new Date()
      });
    } catch (err: any) {
      set({ error: err.message || "An error occurred", loading: false });
    }
  },
  
  setSelectedSatellite: (id) => set({ selectedSatelliteId: id, selectedEventId: null }),
  setSelectedEvent: (id) => set({ selectedEventId: id, selectedSatelliteId: null }),
  setTimeWindow: (hours) => set({ timeWindowHours: hours }),
  setDistanceThreshold: (km) => set({ distanceThresholdKm: km }),
  setFilterFormations: (filter) => set({ filterFormations: filter }),
  setAutoRefreshInterval: (ms) => set({ autoRefreshInterval: ms }),
  setDataSource: (source) => set({ dataSource: source }),
  setStaleTleDays: (days) => set({ staleTleDays: days }),
  setLayerVisibility: (layer, visible) => set((state) => ({
    layerVisibility: { ...state.layerVisibility, [layer]: visible }
  })),
}));
