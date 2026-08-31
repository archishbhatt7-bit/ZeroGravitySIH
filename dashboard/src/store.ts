import { create } from "zustand";
import type {
  Satellite,
  ConjunctionEvent,
  LayerVisibility,
  FocusTarget,
  SearchResult,
} from "./types";

interface DashboardState {
  satellites: Satellite[];
  conjunctions: ConjunctionEvent[];
  loading: boolean;
  error: string | null;
  lastRefresh: Date | null;
  totalScreenedCount: number | null;

  // Selection state
  selectedSatelliteId: number | null;
  selectedEventId: string | null;

  // Conjunctions specific to the selected satellite
  selectedSatConjunctions: ConjunctionEvent[];
  selectedSatConjLoading: boolean;

  // Focus target for globe camera animation
  focusTarget: FocusTarget | null;

  // Search
  searchQuery: string;
  searchResults: SearchResult[];
  searchLoading: boolean;

  // Orbit path for selected satellite
  orbitPath: { lat: number; lng: number; alt: number }[] | null;

  // Analysis mode
  isAnalysisMode: boolean;

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
  setFocusTarget: (target: FocusTarget | null) => void;
  setAnalysisMode: (mode: boolean) => void;
  setTimeWindow: (hours: number) => void;
  setDistanceThreshold: (km: number) => void;
  setFilterFormations: (filter: boolean) => void;
  setAutoRefreshInterval: (ms: number) => void;
  setDataSource: (source: string) => void;
  setStaleTleDays: (days: number) => void;
  setLayerVisibility: (layer: keyof LayerVisibility, visible: boolean | string) => void;
  searchSatellites: (query: string) => Promise<void>;
  setSearchQuery: (query: string) => void;
  clearSearch: () => void;
  setOrbitPath: (
    path: { lat: number; lng: number; alt: number }[] | null,
  ) => void;
  fetchSelectedSatConjunctions: (noradId: number) => Promise<void>;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export const useStore = create<DashboardState>((set, get) => ({
  satellites: [],
  conjunctions: [],
  loading: false,
  error: null,
  lastRefresh: null,
  totalScreenedCount: null,

  selectedSatelliteId: null,
  selectedEventId: null,
  selectedSatConjunctions: [],
  selectedSatConjLoading: false,
  focusTarget: null,

  searchQuery: "",
  searchResults: [],
  searchLoading: false,

  orbitPath: null,

  isAnalysisMode: false,

  timeWindowHours: 24,
  distanceThresholdKm: 50,
  filterFormations: false,
  autoRefreshInterval: 300000,
  dataSource: "active",
  staleTleDays: 9999,

  layerVisibility: {
    activeSatellites: true,
    debris: true,
    rocketBodies: true,
    unknown: true,
    orbitPaths: true,
    conjunctionHighlights: true,
    mapStyle: "day" as "day" | "night",
    autoRotate: false,
  },

  fetchData: async () => {
    set({ loading: true, error: null });
    const state = get();

    // Step 1: Fetch satellites first — show them immediately on the globe
    try {
      const state = get();

      const satRes = await fetch(
        `${API_BASE}/satellites?data_source=${state.dataSource}&max_objects=2000`,
      );

      if (!satRes.ok)
        throw new Error("Failed to fetch data from ZeroGravity API");

      const satData = await satRes.json();

      set({
        satellites: satData.satellites,
        loading: false,
        error: null,
      });
    } catch (err: any) {
      set({ error: err.message || "Failed to fetch satellites", loading: false });
    }

    // Step 2: Fetch conjunctions in the background (heavy computation)
    try {
      const conjRes = await fetch(
        `${API_BASE}/conjunctions?hours=${state.timeWindowHours}&threshold_km=${state.distanceThresholdKm}&filter_formations=${state.filterFormations}&data_source=${state.dataSource}&max_objects=2000&stale_tle_days=${state.staleTleDays}`,
      );
      if (conjRes.ok) {
        const conjData = await conjRes.json();
        set({
          conjunctions: conjData.conjunctions,
          lastRefresh: new Date(),
        });
      }
    } catch {
      // Conjunctions failing is non-fatal — globe still works
    }
  },

  setSelectedSatellite: (id) => {
    set({ selectedSatelliteId: id, selectedEventId: null, selectedSatConjunctions: [], selectedSatConjLoading: false });
    // Auto-fetch conjunctions for the selected satellite
    if (id !== null) {
      get().fetchSelectedSatConjunctions(id);
    }
  },
  setSelectedEvent: (id) =>
    set({ selectedEventId: id, selectedSatelliteId: null }),
  setFocusTarget: (target) => set({ focusTarget: target }),
  setAnalysisMode: (mode) =>
    set({
      isAnalysisMode: mode,
      // Clear selections when exiting analysis mode
      ...(!mode ? { selectedEventId: null, orbitPath: null } : {}),
    }),
  setTimeWindow: (hours) => {
    set({ timeWindowHours: hours });
    const state = get();
    if (state.selectedSatelliteId) {
      state.fetchSelectedSatConjunctions(state.selectedSatelliteId);
    }
  },
  setDistanceThreshold: (km) => {
    set({ distanceThresholdKm: km });
    const state = get();
    if (state.selectedSatelliteId) {
      state.fetchSelectedSatConjunctions(state.selectedSatelliteId);
    }
  },
  setFilterFormations: (filter) => {
    set({ filterFormations: filter });
    const state = get();
    if (state.selectedSatelliteId) {
      state.fetchSelectedSatConjunctions(state.selectedSatelliteId);
    }
  },
  setAutoRefreshInterval: (ms) => set({ autoRefreshInterval: ms }),
  setDataSource: (source) => set({ dataSource: source }),
  setStaleTleDays: (days) => set({ staleTleDays: days }),
  setLayerVisibility: (layer, visible) =>
    set((state) => ({
      layerVisibility: { ...state.layerVisibility, [layer]: visible },
    })),
  setOrbitPath: (path) => set({ orbitPath: path }),

  setSearchQuery: (query) => set({ searchQuery: query }),
  clearSearch: () =>
    set({ searchQuery: "", searchResults: [], searchLoading: false }),

  searchSatellites: async (query: string) => {
    if (!query.trim()) {
      set({ searchResults: [], searchLoading: false });
      return;
    }
    set({ searchLoading: true });
    try {
      const res = await fetch(
        `${API_BASE}/satellites/search?q=${encodeURIComponent(query)}&limit=20`,
      );
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      set({ searchResults: data.results, searchLoading: false });
    } catch {
      set({ searchResults: [], searchLoading: false });
    }
  },

  fetchSelectedSatConjunctions: async (noradId: number) => {
    set({ selectedSatConjLoading: true });
    try {
      const state = get();
      const res = await fetch(
        `${API_BASE}/screen/${noradId}?hours=${state.timeWindowHours}&threshold_km=${state.distanceThresholdKm}&filter_formations=${state.filterFormations}`,
      );
      if (res.ok) {
        const data = await res.json();
        // Only set if this satellite is still selected
        if (get().selectedSatelliteId === noradId) {
          set({ selectedSatConjunctions: data.conjunctions, selectedSatConjLoading: false });
        }
      } else {
        set({ selectedSatConjLoading: false });
      }
    } catch {
      set({ selectedSatConjLoading: false });
    }
  },
}));
