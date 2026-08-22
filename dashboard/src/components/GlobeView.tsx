import { useEffect, useRef, useState, useMemo } from 'react';
import Globe from 'react-globe.gl';
import { useStore } from '../store';

export function GlobeView() {
  const globeEl = useRef<any>();
  const [globeReady, setGlobeReady] = useState(false);
  const { satellites, conjunctions, selectedSatelliteId, selectedEventId, setSelectedSatellite } = useStore();

  useEffect(() => {
    // Make globe rotate slightly and set initial position
    if (globeEl.current) {
      globeEl.current.controls().autoRotate = true;
      globeEl.current.controls().autoRotateSpeed = 0.5;
      globeEl.current.pointOfView({ altitude: 2.5 });
      setGlobeReady(true);
    }
  }, []);

  // Compute satellite points for rendering
  const satData = useMemo(() => {
    // Since calculating exact lat/lon for 9000 objects every frame is expensive,
    // we'll just plot them randomly or use approximate initial positions for the visual
    // In a real app we'd use satellite.js to get exact lat/lon/alt from TLEs.
    
    // For demo purposes, we will roughly position them.
    return satellites.map(sat => {
      // Very rough approximation for visual effect
      const lat = (Math.random() - 0.5) * 180; // random lat
      const lng = (Math.random() - 0.5) * 360; // random lng
      const alt = 0.05 + (Math.random() * 0.1); // LEO altitude approx
      
      let color = 'rgba(255, 255, 255, 0.5)';
      if (sat.object_type === 'ACTIVE_SATELLITE') color = 'rgba(0, 240, 255, 0.8)';
      if (sat.object_type === 'DEBRIS') color = 'rgba(150, 150, 150, 0.6)';
      if (sat.object_type === 'ROCKET_BODY') color = 'rgba(234, 179, 8, 0.7)';
      
      return {
        lat,
        lng,
        alt,
        color,
        radius: sat.object_type === 'ACTIVE_SATELLITE' ? 0.02 : 0.01,
        sat
      };
    });
  }, [satellites]);

  // Highlight conjunction points
  const ringsData = useMemo(() => {
    if (!globeReady) return [];
    
    // We would ideally compute the exact lat/lon at TCA.
    // For now, we just spawn a ring at a random location representing the event.
    return conjunctions.slice(0, 50).map(c => ({
      lat: (Math.random() - 0.5) * 180,
      lng: (Math.random() - 0.5) * 360,
      maxR: c.risk_category === 'CRITICAL' ? 5 : c.risk_category === 'HIGH' ? 3 : 1.5,
      propagationSpeed: 1.5,
      repeatPeriod: 1000,
      color: c.risk_category === 'CRITICAL' ? '#ef4444' : c.risk_category === 'HIGH' ? '#f97316' : '#eab308'
    }));
  }, [conjunctions, globeReady]);

  return (
    <div className="absolute inset-0 z-0">
      <Globe
        ref={globeEl}
        globeImageUrl="//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
        bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
        backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
        pointsData={satData}
        pointLat="lat"
        pointLng="lng"
        pointAltitude="alt"
        pointColor="color"
        pointRadius="radius"
        pointsMerge={true}
        ringsData={ringsData}
        ringColor="color"
        ringMaxRadius="maxR"
        ringPropagationSpeed="propagationSpeed"
        ringRepeatPeriod="repeatPeriod"
        onPointClick={(pt: any) => setSelectedSatellite(pt.sat.norad_id)}
      />
    </div>
  );
}
