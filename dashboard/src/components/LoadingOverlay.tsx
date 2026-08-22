import { useStore } from '../store';
import { Loader2 } from 'lucide-react';

export function LoadingOverlay() {
  const { loading } = useStore();

  if (!loading) return null;

  return (
    <div className="absolute inset-0 bg-[#05060a]/80 backdrop-blur-sm z-50 flex flex-col items-center justify-center">
      <Loader2 className="w-12 h-12 text-cyan-400 animate-spin mb-4" />
      <h2 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
        Scanning Catalog...
      </h2>
      <p className="text-slate-400 mt-2 font-mono text-sm">
        Propagating orbits and checking for close approaches
      </p>
    </div>
  );
}
