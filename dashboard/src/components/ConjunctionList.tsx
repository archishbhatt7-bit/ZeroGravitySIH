import { useStore } from '../store';
import { format } from 'date-fns';

export function ConjunctionList() {
  const { conjunctions, setSelectedEvent, selectedEventId } = useStore();

  const getBadgeColor = (category: string) => {
    switch (category) {
      case 'CRITICAL': return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'HIGH': return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
      case 'MEDIUM': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'LOW': return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  return (
    <div className="absolute top-24 right-6 glass-panel w-96 flex flex-col p-4 max-h-[calc(100vh-120px)]">
      <h2 className="text-lg font-semibold text-slate-200 mb-4 pb-2 border-b border-white/10">
        Active Conjunction Alerts ({conjunctions.length})
      </h2>
      
      <div className="flex-1 overflow-y-auto pr-2 space-y-3 -mr-2">
        {conjunctions.length === 0 ? (
          <div className="text-center text-slate-500 py-8">
            No conjunctions detected within parameters.
          </div>
        ) : (
          conjunctions.map((c, i) => {
            const id = `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}`;
            const isSelected = selectedEventId === id;
            
            return (
              <div 
                key={id + i}
                onClick={() => setSelectedEvent(id)}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected 
                    ? 'bg-slate-800/80 border-cyan-500/50 shadow-[0_0_15px_rgba(0,240,255,0.15)]' 
                    : 'bg-slate-900/50 border-white/5 hover:border-white/20 hover:bg-slate-800/50'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getBadgeColor(c.risk_category)}`}>
                    {c.risk_category}
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    TCA: {format(new Date(c.tca), 'HH:mm:ss')}
                  </span>
                </div>
                
                <div className="text-sm font-semibold truncate text-slate-200" title={c.primary.name}>
                  1: {c.primary.name}
                </div>
                <div className="text-sm font-semibold truncate text-slate-200" title={c.secondary.name}>
                  2: {c.secondary.name}
                </div>
                
                <div className="flex justify-between mt-3 text-xs font-mono">
                  <div className="flex flex-col">
                    <span className="text-slate-500">MISS DIST</span>
                    <span className="text-cyan-400">{c.miss_distance_km.toFixed(2)} km</span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-slate-500">SCORE</span>
                    <span className="text-slate-200">{c.risk_score.toFixed(1)}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
