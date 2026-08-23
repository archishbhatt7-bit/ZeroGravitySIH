import { useStore } from '../store';
import { Layers, Eye, EyeOff } from 'lucide-react';

const LAYER_CONFIG = [
  { key: 'activeSatellites' as const, label: 'Active Satellites', color: 'bg-cyan-400' },
  { key: 'debris' as const, label: 'Debris', color: 'bg-gray-400' },
  { key: 'rocketBodies' as const, label: 'Rocket Bodies', color: 'bg-yellow-400' },
  { key: 'unknown' as const, label: 'Unknown', color: 'bg-slate-500' },
  { key: 'orbitPaths' as const, label: 'Orbit Paths', color: 'bg-cyan-500' },
  { key: 'conjunctionHighlights' as const, label: 'Conjunctions', color: 'bg-red-500' },
];

export function LayerToggles() {
  const { layerVisibility, setLayerVisibility } = useStore();

  return (
    <div className="absolute bottom-6 right-6 glass-panel p-3 z-20 w-52 hover-lift">
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/10">
        <Layers className="w-4 h-4 text-cyan-400" />
        <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Layers</h3>
      </div>
      
      <div className="space-y-1.5">
        {LAYER_CONFIG.map(({ key, label, color }) => {
          const isVisible = layerVisibility[key] as boolean;
          return (
            <button
              key={key}
              onClick={() => setLayerVisibility(key, !isVisible)}
              className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded text-xs transition-all ${
                isVisible 
                  ? 'text-slate-200 hover:bg-white/5' 
                  : 'text-slate-600 hover:bg-white/5'
              }`}
            >
              <div className={`w-2.5 h-2.5 rounded-full ${color} transition-opacity ${isVisible ? 'opacity-100' : 'opacity-20'}`} />
              <span className="flex-1 text-left">{label}</span>
              {isVisible 
                ? <Eye className="w-3.5 h-3.5 text-slate-500" /> 
                : <EyeOff className="w-3.5 h-3.5 text-slate-600" />
              }
            </button>
          );
        })}
      </div>
      
      <div className="mt-4 pt-3 border-t border-white/10 space-y-2">
        <button
          onClick={() => setLayerVisibility('mapStyle', layerVisibility.mapStyle === 'day' ? 'night' : 'day')}
          className="w-full flex items-center justify-between px-2 py-1.5 rounded text-xs text-slate-300 hover:bg-white/5 transition-all"
        >
          <span>Map Style</span>
          <span className="text-[10px] uppercase font-mono bg-slate-800 px-1.5 py-0.5 rounded text-cyan-400">
            {layerVisibility.mapStyle || 'day'}
          </span>
        </button>

        <button
          onClick={() => setLayerVisibility('autoRotate', !layerVisibility.autoRotate)}
          className="w-full flex items-center justify-between px-2 py-1.5 rounded text-xs text-slate-300 hover:bg-white/5 transition-all"
        >
          <span>Auto Rotate</span>
          {layerVisibility.autoRotate 
            ? <Eye className="w-3.5 h-3.5 text-cyan-400" /> 
            : <EyeOff className="w-3.5 h-3.5 text-slate-600" />
          }
        </button>
      </div>
    </div>
  );
}
