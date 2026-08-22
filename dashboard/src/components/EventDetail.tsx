import { useStore } from '../store';
import { X, AlertOctagon } from 'lucide-react';
import { format } from 'date-fns';

export function EventDetail() {
  const { conjunctions, selectedEventId, setSelectedEvent } = useStore();

  if (!selectedEventId) return null;

  const event = conjunctions.find(c => 
    `${c.primary.norad_id}-${c.secondary.norad_id}-${c.tca}` === selectedEventId
  );

  if (!event) return null;

  const isCritical = event.risk_category === 'CRITICAL' || event.risk_category === 'HIGH';

  return (
    <div className="absolute top-24 left-1/2 -translate-x-1/2 glass-panel w-[500px] p-6 !h-auto shadow-2xl">
      <button 
        onClick={() => setSelectedEvent(null)}
        className="absolute top-4 right-4 text-slate-400 hover:text-white"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="flex items-center gap-3 mb-6">
        <AlertOctagon className={`w-8 h-8 ${isCritical ? 'text-red-500' : 'text-yellow-500'}`} />
        <div>
          <h2 className="text-xl font-bold text-slate-100">Conjunction Event Assessment</h2>
          <p className={`text-sm font-mono ${isCritical ? 'text-red-400' : 'text-yellow-400'}`}>
            RISK: {event.risk_category} (Score: {event.risk_score.toFixed(1)})
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-slate-900/50 p-3 rounded-lg border border-white/5">
          <div className="text-[10px] text-slate-500 mb-1">PRIMARY OBJECT</div>
          <div className="font-bold text-sm text-cyan-400 truncate" title={event.primary.name}>{event.primary.name}</div>
          <div className="text-xs font-mono text-slate-400 mt-1">NORAD ID: {event.primary.norad_id}</div>
          <div className="flex gap-2 mt-2 text-[10px] uppercase">
            <span className="bg-slate-800 px-1.5 py-0.5 rounded">{event.primary.object_type.replace('_', ' ')}</span>
            <span className="bg-slate-800 px-1.5 py-0.5 rounded">RCS: {event.primary.rcs}</span>
          </div>
        </div>

        <div className="bg-slate-900/50 p-3 rounded-lg border border-white/5">
          <div className="text-[10px] text-slate-500 mb-1">SECONDARY OBJECT</div>
          <div className="font-bold text-sm text-orange-400 truncate" title={event.secondary.name}>{event.secondary.name}</div>
          <div className="text-xs font-mono text-slate-400 mt-1">NORAD ID: {event.secondary.norad_id}</div>
          <div className="flex gap-2 mt-2 text-[10px] uppercase">
            <span className="bg-slate-800 px-1.5 py-0.5 rounded">{event.secondary.object_type.replace('_', ' ')}</span>
            <span className="bg-slate-800 px-1.5 py-0.5 rounded">RCS: {event.secondary.rcs}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-6 text-center">
        <div className="bg-slate-800/30 p-2 rounded">
          <div className="text-[10px] text-slate-500">TIME TO TCA</div>
          <div className="text-sm font-mono text-slate-200">
            {event.time_to_tca_hours ? `${event.time_to_tca_hours.toFixed(1)} hrs` : 'N/A'}
          </div>
        </div>
        <div className="bg-slate-800/30 p-2 rounded border border-cyan-500/20">
          <div className="text-[10px] text-slate-500">MISS DISTANCE</div>
          <div className="text-sm font-mono text-cyan-400">{event.miss_distance_km.toFixed(3)} km</div>
        </div>
        <div className="bg-slate-800/30 p-2 rounded">
          <div className="text-[10px] text-slate-500">REL VELOCITY</div>
          <div className="text-sm font-mono text-slate-200">{event.relative_velocity_km_s.toFixed(2)} km/s</div>
        </div>
      </div>

      <div className="bg-slate-900/80 p-4 rounded-lg border border-white/10 mb-4">
        <div className="text-xs text-slate-400 mb-2 font-semibold">ACTION RECOMMENDATION</div>
        <div className={`text-sm ${isCritical ? 'text-red-400' : 'text-slate-200'}`}>
          {event.recommendation}
        </div>
      </div>

      <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
        <span>TCA: {format(new Date(event.tca), 'yyyy-MM-dd HH:mm:ss')} UTC</span>
        <button className="px-3 py-1 bg-cyan-600/20 text-cyan-400 border border-cyan-600/50 rounded hover:bg-cyan-600/30 transition-colors">
          FOCUS ON GLOBE
        </button>
      </div>
    </div>
  );
}
