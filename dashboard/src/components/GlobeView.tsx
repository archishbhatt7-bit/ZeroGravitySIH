import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import Globe from 'react-globe.gl';
import * as satellite from 'satellite.js';
import * as THREE from 'three';
import { useStore } from '../store';

interface SatPoint {
  lat: number;
  lng: number;
  alt: number;
  color: string;
  radius: number;
  sat: { norad_id: number; name: string; object_type: string };
}

export function GlobeView() {
  const globeEl = useRef<any>();
  const [globeReady, setGlobeReady] = useState(false);
  const satrecsRef = useRef<Map<number, any>>(new Map());
  const [satPositions, setSatPositions] = useState<SatPoint[]>([]);
  
  const { 
    satellites, conjunctions, selectedSatelliteId, selectedEventId,
    setSelectedSatellite, focusTarget, setFocusTarget,
    layerVisibility, isAnalysisMode
  } = useStore();

  // Initialize globe
  useEffect(() => {
    if (globeEl.current) {
      globeEl.current.controls().autoRotate = !!layerVisibility.autoRotate;
      globeEl.current.controls().autoRotateSpeed = 0.3;
      globeEl.current.controls().enableZoom = true;
      if (!globeReady) {
        globeEl.current.pointOfView({ altitude: 2.5 });
        setGlobeReady(true);
      }
    }
  }, [layerVisibility.autoRotate, globeReady]);

  // Parse TLEs into satrecs (cached)
  useEffect(() => {
    const map = new Map<number, any>();
    for (const sat of satellites) {
      try {
        const satrec = satellite.twoline2satrec(sat.line1, sat.line2);
        map.set(sat.norad_id, satrec);
      } catch {
        // Skip invalid TLEs
      }
    }
    satrecsRef.current = map;
  }, [satellites]);

  // Compute real satellite positions via satellite.js, update every 10s
  const computePositions = useCallback(() => {
    const now = new Date();
    const gmst = satellite.gstime(now);
    const points: SatPoint[] = [];
    const state = useStore.getState();
    const visibility = state.layerVisibility;
    const mode = state.isAnalysisMode;
    const eventId = state.selectedEventId;
    
    // Create a set of NORAD IDs that should be visible in analysis mode
    const analysisNoradIds = new Set<number>();
    if (mode) {
      if (eventId) {
        // Only show satellites for the selected event
        const event = state.conjunctions.find(c => `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}` === eventId);
        if (event) {
          analysisNoradIds.add(event.primary.norad_id);
          analysisNoradIds.add(event.secondary.norad_id);
        }
      } else {
        // Show all satellites involved in any conjunction
        state.conjunctions.forEach(c => {
          analysisNoradIds.add(c.primary.norad_id);
          analysisNoradIds.add(c.secondary.norad_id);
        });
      }
    }

    for (const sat of satellites) {
      // In analysis mode, filter out unneeded satellites
      if (mode && !analysisNoradIds.has(sat.norad_id)) continue;
      
      // Filter by layer visibility (only applies if not in analysis mode, or if they are in analysis mode we can ignore layer toggles or keep them)
      if (!mode) {
        if (sat.object_type === 'ACTIVE_SATELLITE' && !visibility.activeSatellites) continue;
        if (sat.object_type === 'DEBRIS' && !visibility.debris) continue;
        if (sat.object_type === 'ROCKET_BODY' && !visibility.rocketBodies) continue;
        if (sat.object_type === 'UNKNOWN' && !visibility.unknown) continue;
      }

      const satrec = satrecsRef.current.get(sat.norad_id);
      if (!satrec) continue;

      try {
        const posVel = satellite.propagate(satrec, now);
        if (posVel.position && typeof posVel.position !== 'boolean') {
          const geodetic = satellite.eciToGeodetic(posVel.position, gmst);
          const lat = satellite.degreesLat(geodetic.latitude);
          const lng = satellite.degreesLong(geodetic.longitude);
          const alt = geodetic.height / 6371; // Normalize to globe scale

          let color = 'rgba(255, 255, 255, 0.4)';
          let radius = 0.4; // Scaled for THREE.SphereGeometry

          if (sat.object_type === 'ACTIVE_SATELLITE') {
            color = '#00f0ff';
            radius = 0.8;
          } else if (sat.object_type === 'DEBRIS') {
            color = '#999999';
            radius = 0.3;
          } else if (sat.object_type === 'ROCKET_BODY') {
            color = '#eab308';
            radius = 0.6;
          }

          // Highlight selected
          if (sat.norad_id === useStore.getState().selectedSatelliteId) {
            color = '#ffffff';
            radius = 1.5;
          }

          points.push({
            lat, lng, alt,
            color, radius,
            sat: { norad_id: sat.norad_id, name: sat.name, object_type: sat.object_type }
          });
        }
      } catch {
        // Skip propagation errors
      }
    }
    setSatPositions(points);
  }, [satellites]);

  // Initial computation and periodic updates
  useEffect(() => {
    if (satellites.length === 0) return;
    const timer = setTimeout(() => {
      computePositions();
    }, 100);
    const interval = setInterval(computePositions, 10000); // Update every 10s
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [satellites, computePositions]);

  // Recompute when layer visibility changes
  useEffect(() => {
    if (satellites.length > 0) {
      computePositions();
    }
  }, [layerVisibility, isAnalysisMode, selectedEventId, selectedSatelliteId, computePositions, satellites.length]);

  // Conjunction rings — real positions from API
  const ringsData = useMemo(() => {
    if (!globeReady || !layerVisibility.conjunctionHighlights) return [];
    
    return conjunctions.slice(0, 80).map(c => ({
      lat: c.lat,
      lng: c.lng,
      maxR: c.risk_category === 'CRITICAL' ? 5 : c.risk_category === 'HIGH' ? 3 : 1.5,
      propagationSpeed: c.risk_category === 'CRITICAL' ? 2.5 : 1.5,
      repeatPeriod: c.risk_category === 'CRITICAL' ? 600 : 1000,
      color: c.risk_category === 'CRITICAL' ? '#ef4444' 
           : c.risk_category === 'HIGH' ? '#f97316' 
           : c.risk_category === 'MEDIUM' ? '#eab308'
           : 'rgba(100, 120, 255, 0.5)',
    }));
  }, [conjunctions, globeReady, layerVisibility.conjunctionHighlights]);

  // Orbit arc path for selected satellite or conjunction
  const pathsData = useMemo(() => {
    if (!globeReady || !layerVisibility.orbitPaths) return [];
    
    const paths = [];
    const now = new Date();
    
    // Helper to generate path for a satellite
    const getPath = (satrec: any, startTime: Date, durationMins: number, color: string[]) => {
      const coords = [];
      for (let i = 0; i <= durationMins; i += 2) { // 2 minute steps for smoothness
        const t = new Date(startTime.getTime() + i * 60000);
        const gmst = satellite.gstime(t);
        const posVel = satellite.propagate(satrec, t);
        if (posVel.position && typeof posVel.position !== 'boolean') {
          const geodetic = satellite.eciToGeodetic(posVel.position, gmst);
          coords.push([
            satellite.degreesLat(geodetic.latitude),
            satellite.degreesLong(geodetic.longitude),
            geodetic.height / 6371
          ]);
        }
      }
      return { coords, color };
    };

    if (selectedEventId) {
      // Show paths for both satellites involved in the conjunction
      const event = conjunctions.find(c => `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}` === selectedEventId);
      if (event) {
        let sat1 = satrecsRef.current.get(event.primary.norad_id);
        if (!sat1 && event.primary.line1 && event.primary.line2) {
          try { sat1 = satellite.twoline2satrec(event.primary.line1, event.primary.line2); } catch {}
        }
        
        let sat2 = satrecsRef.current.get(event.secondary.norad_id);
        if (!sat2 && event.secondary.line1 && event.secondary.line2) {
          try { sat2 = satellite.twoline2satrec(event.secondary.line1, event.secondary.line2); } catch {}
        }
        
        const tca = new Date(event.tca);
        // Path from 45 mins before TCA to 45 mins after TCA
        const start = new Date(tca.getTime() - 45 * 60000);
        
        if (sat1) paths.push(getPath(sat1, start, 90, ['rgba(0, 240, 255, 1)', 'rgba(0, 240, 255, 0.1)']));
        if (sat2) paths.push(getPath(sat2, start, 90, ['rgba(255, 150, 0, 1)', 'rgba(255, 150, 0, 0.1)']));
      }
    } else if (selectedSatelliteId) {
      // Show path for single selected satellite
      const sat = satrecsRef.current.get(selectedSatelliteId);
      if (sat) {
        paths.push(getPath(sat, now, 90, ['rgba(0, 240, 255, 1)', 'rgba(0, 240, 255, 0.1)']));
      }
    }
    
    return paths;
  }, [selectedEventId, selectedSatelliteId, conjunctions, globeReady, layerVisibility.orbitPaths]);

  // Camera animation when focusTarget changes
  useEffect(() => {
    if (focusTarget && globeEl.current) {
      globeEl.current.controls().autoRotate = false; // Always stop rotation when zooming to target
      globeEl.current.pointOfView(
        { lat: focusTarget.lat, lng: focusTarget.lng, altitude: 1.5 },
        1500
      );
      setTimeout(() => setFocusTarget(null), 1600);
    }
  }, [focusTarget, setFocusTarget]);

  return (
    <div className="absolute inset-0 z-0">
      <Globe
        ref={globeEl}
        globeImageUrl={layerVisibility.mapStyle === 'night' 
          ? "//unpkg.com/three-globe/example/img/earth-night.jpg"
          : "//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
        }
        bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
        backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
        atmosphereColor="#00aaff"
        atmosphereAltitude={0.2}
        
        // Render satellites as floating 3D objects instead of vertical bars
        objectsData={satPositions}
        objectLat="lat"
        objectLng="lng"
        objectAltitude="alt"
        objectThreeObject={(d: any) => {
          return new THREE.Mesh(
            new THREE.SphereGeometry(d.radius),
            new THREE.MeshBasicMaterial({ color: d.color })
          );
        }}
        
        ringsData={ringsData}
        ringColor="color"
        ringMaxRadius="maxR"
        ringPropagationSpeed="propagationSpeed"
        ringRepeatPeriod="repeatPeriod"
        
        pathsData={pathsData}
        pathPoints="coords"
        pathPointLat={(p: any) => p[0]}
        pathPointLng={(p: any) => p[1]}
        pathPointAlt={(p: any) => p[2]}
        pathColor="color"
        pathStroke={2.5}
        pathDashLength={0.05}
        pathDashGap={0.02}
        pathDashAnimateTime={4000}
        
        onObjectClick={(pt: any) => {
          setSelectedSatellite(pt.sat.norad_id);
          setFocusTarget({ lat: pt.lat, lng: pt.lng, alt: pt.alt });
        }}
      />
    </div>
  );
}
