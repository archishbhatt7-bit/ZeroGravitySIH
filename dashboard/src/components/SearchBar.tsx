import { useState, useEffect, useRef } from 'react';
import { useStore } from '../store';
import { Search, X, Loader2, Satellite } from 'lucide-react';

export function SearchBar() {
  const { searchQuery, searchResults, searchLoading, setSearchQuery, searchSatellites, clearSearch, setSelectedSatellite, setFocusTarget } = useStore();
  const [isOpen, setIsOpen] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const handleInputChange = (value: string) => {
    setSearchQuery(value);
    setHighlightIdx(-1);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      searchSatellites(value);
    }, 300);
  };

  const handleSelect = (result: any) => {
    setSelectedSatellite(result.norad_id);
    if (result.lat !== undefined && result.lng !== undefined) {
      setFocusTarget({ lat: result.lat, lng: result.lng, alt: result.alt || 400 });
    }
    clearSearch();
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightIdx(prev => Math.min(prev + 1, searchResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightIdx(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && highlightIdx >= 0) {
      handleSelect(searchResults[highlightIdx]);
    } else if (e.key === 'Escape') {
      clearSearch();
      setIsOpen(false);
    }
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest('.search-container')) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ACTIVE_SATELLITE': return 'text-cyan-400';
      case 'DEBRIS': return 'text-slate-500';
      case 'ROCKET_BODY': return 'text-yellow-500';
      default: return 'text-slate-400';
    }
  };

  return (
    <div className="search-container absolute top-20 left-6 z-20 w-80">
      {/* Search Input */}
      <div className="glass-panel flex items-center gap-2 px-3 py-2 rounded-lg hover-lift">
        <Search className="w-4 h-4 text-slate-400 shrink-0" />
        <input
          ref={inputRef}
          type="text"
          value={searchQuery}
          onChange={e => {
            handleInputChange(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search by name or NORAD ID..."
          className="bg-transparent border-none outline-none text-sm text-white placeholder-slate-500 w-full font-mono"
        />
        {searchLoading && <Loader2 className="w-4 h-4 text-cyan-400 animate-spin shrink-0" />}
        {searchQuery && !searchLoading && (
          <button onClick={() => { clearSearch(); setIsOpen(false); }} className="text-slate-500 hover:text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Results Dropdown */}
      {isOpen && searchResults.length > 0 && (
        <div className="glass-panel mt-1 rounded-lg overflow-hidden max-h-72 overflow-y-auto slide-in-down">
          {searchResults.map((result, i) => (
            <button
              key={result.norad_id}
              onClick={() => handleSelect(result)}
              className={`w-full text-left px-3 py-2.5 flex items-center gap-3 transition-all border-b border-white/5 last:border-b-0 ${
                i === highlightIdx
                  ? 'bg-cyan-500/15 border-l-2 border-l-cyan-400'
                  : 'hover:bg-white/5'
              }`}
            >
              <Satellite className={`w-4 h-4 shrink-0 ${getTypeColor(result.object_type)}`} />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-slate-200 truncate">{result.name}</div>
                <div className="flex gap-3 text-[10px] font-mono text-slate-500 mt-0.5">
                  <span>#{result.norad_id}</span>
                  <span>{result.object_type.replace('_', ' ')}</span>
                  {result.alt !== undefined && <span>{result.alt.toFixed(0)} km</span>}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {isOpen && searchQuery && !searchLoading && searchResults.length === 0 && (
        <div className="glass-panel mt-1 rounded-lg px-4 py-6 text-center text-slate-500 text-sm slide-in-down">
          No satellites found
        </div>
      )}
    </div>
  );
}
