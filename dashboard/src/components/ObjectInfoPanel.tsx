import { useStore } from '../store';
import { X, Satellite, Activity } from 'lucide-react';
import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import * as satellite from 'satellite.js';

export function ObjectInfoPanel() {
  const { satellites, selectedSatelliteId, setSelectedSatellite, conjunctions } = useStore();
  const [position, setPosition] = useState<{ lat: number; lng: number; alt: number; vel: number } | null>(null);

  const sat = satellites.find(s => s.norad_id === selectedSatelliteId);

  useEffect(() => {
    if (!sat) return;

    // Update position every second
    const updatePosition = () => {
      try {
        const satrec = satellite.twoline2satrec(sat.line1, sat.line2);
        const date = new Date();
        const posVel = satellite.propagate(satrec, date);
        const gmst = satellite.gstime(date);
        
        if (posVel.position && typeof posVel.position !== 'boolean') {
          const geodetic = satellite.eciToGeodetic(posVel.position, gmst);
          
          let velocity = 0;
          if (posVel.velocity && typeof posVel.velocity !== 'boolean') {
            const v = posVel.velocity as { x: number, y: number, z: number };
            velocity = Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
          }
          
          setPosition({
            lat: satellite.degreesLat(geodetic.latitude),
            lng: satellite.degreesLong(geodetic.longitude),
            alt: geodetic.height,
            vel: velocity
          });
        }
      } catch (e) {
        console.error("Error computing position for", sat.name, e);
      }
    };

    updatePosition();
    const interval = setInterval(updatePosition, 1000);
    return () => clearInterval(interval);
  }, [sat]);

  if (!sat) return null;

  const ageDays = (new Date().getTime() - new Date(sat.epoch).getTime()) / (1000 * 60 * 60 * 24);
  const isStale = ageDays > 3;

  const activeConjunctions = conjunctions.filter(c => 
    c.primary.norad_id === sat.norad_id || c.secondary.norad_id === sat.norad_id
  );

  return (
    <div className="absolute top-24 left-6 glass-panel w-80 p-5 shadow-2xl z-30">
      <button 
        onClick={() => setSelectedSatellite(null)}
        className="absolute top-4 right-4 text-slate-400 hover:text-white"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="flex items-center gap-3 mb-4">
        <Satellite className="w-6 h-6 text-cyan-400" />
        <div>
          <h2 className="text-lg font-bold text-slate-100 truncate w-48" title={sat.name}>{sat.name}</h2>
          <p className="text-xs font-mono text-slate-400">NORAD: {sat.norad_id}</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="bg-slate-900/50 p-3 rounded-lg border border-white/5">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-slate-500 block mb-0.5">TYPE</span>
              <span className="text-slate-200">{sat.object_type.replace('_', ' ')}</span>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">INCLINATION</span>
              <span className="font-mono text-cyan-400">{sat.inclination.toFixed(2)}°</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-900/50 p-3 rounded-lg border border-white/5 relative">
          <div className="text-[10px] text-slate-500 mb-1">TLE DATA AGE</div>
          <div className="font-mono text-sm flex items-center justify-between">
            <span className={isStale ? "text-red-400" : "text-green-400"}>
              {ageDays.toFixed(1)} days
            </span>
            {isStale && (
              <span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded border border-red-500/30">
                STALE
              </span>
            )}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">
            Epoch: {format(new Date(sat.epoch), 'yyyy-MM-dd HH:mm')}
          </div>
        </div>

        {position && (
          <div className="bg-slate-900/50 p-3 rounded-lg border border-white/5">
            <div className="text-[10px] text-slate-500 mb-2 flex items-center gap-1">
              <Activity className="w-3 h-3 text-cyan-500" /> LIVE TELEMETRY
            </div>
            <div className="grid grid-cols-2 gap-y-2 text-xs font-mono">
              <div>
                <span className="text-slate-500 block">LAT</span>
                <span className="text-slate-200">{position.lat.toFixed(4)}°</span>
              </div>
              <div>
                <span className="text-slate-500 block">LON</span>
                <span className="text-slate-200">{position.lng.toFixed(4)}°</span>
              </div>
              <div>
                <span className="text-slate-500 block">ALT</span>
                <span className="text-cyan-400">{position.alt.toFixed(1)} km</span>
              </div>
              <div>
                <span className="text-slate-500 block">VEL</span>
                <span className="text-slate-200">{position.vel.toFixed(2)} km/s</span>
              </div>
            </div>
          </div>
        )}

        {activeConjunctions.length > 0 && (
          <div className="bg-red-900/20 p-3 rounded-lg border border-red-500/30">
            <div className="text-xs font-bold text-red-400 mb-2">
              {activeConjunctions.length} Active Alerts
            </div>
            <div className="max-h-24 overflow-y-auto space-y-1 pr-1">
              {activeConjunctions.map((c, i) => (
                <div key={i} className="text-[10px] font-mono flex justify-between items-center bg-black/20 p-1.5 rounded">
                  <span className="text-slate-300 truncate w-24">
                    vs {c.primary.norad_id === sat.norad_id ? c.secondary.name : c.primary.name}
                  </span>
                  <span className="text-cyan-400">{c.miss_distance_km.toFixed(1)} km</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
