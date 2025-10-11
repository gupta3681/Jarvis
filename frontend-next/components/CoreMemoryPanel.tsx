import { useState } from 'react';
import { useCoreMemory } from '@/hooks/useCoreMemory';
import { Brain, Briefcase, Heart, User, Users, Settings, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';

export function CoreMemoryPanel() {
  const { coreMemory, loading, error, refetch } = useCoreMemory();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['identity', 'work']));

  const toggleSection = (key: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedSections(newExpanded);
  };

  if (loading) {
    return (
      <div className="p-4 text-white/70 text-sm flex items-center gap-2">
        <RefreshCw className="w-4 h-4 animate-spin" />
        Loading memory...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-300 text-sm">
        Error: {error}
      </div>
    );
  }

  if (!coreMemory) {
    return null;
  }

  const sections = [
    { key: 'identity', icon: User, label: 'Identity', data: coreMemory.identity },
    { key: 'work', icon: Briefcase, label: 'Work', data: coreMemory.work },
    { key: 'preferences', icon: Heart, label: 'Preferences', data: coreMemory.preferences },
    { key: 'health', icon: Brain, label: 'Health', data: coreMemory.health },
    { key: 'relationships', icon: Users, label: 'Relationships', data: coreMemory.relationships },
  ];

  const hasAnyData = sections.some(section => Object.keys(section.data).length > 0);

  return (
    <div className="px-6 py-4 border-t border-white/10">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white/90 flex items-center gap-2">
          <Brain className="w-4 h-4" />
          Core Memory
        </h3>
        <button
          onClick={refetch}
          className="p-1 hover:bg-white/10 rounded transition-colors"
          title="Refresh memory"
        >
          <RefreshCw className="w-3 h-3 text-white/60" />
        </button>
      </div>

      {!hasAnyData ? (
        <p className="text-xs text-white/50 italic">No core memory stored yet</p>
      ) : (
        <div className="space-y-2">
          {sections.map(({ key, icon: Icon, label, data }) => {
            const entries = Object.entries(data);
            if (entries.length === 0) return null;

            const isExpanded = expandedSections.has(key);

            return (
              <div key={key} className="space-y-1">
                <button
                  onClick={() => toggleSection(key)}
                  className="w-full flex items-center gap-1.5 text-xs text-white/70 hover:text-white/90 transition-colors py-1 px-2 hover:bg-white/5 rounded"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3" />
                  ) : (
                    <ChevronRight className="w-3 h-3" />
                  )}
                  <Icon className="w-3 h-3" />
                  <span className="font-medium">{label}</span>
                  <span className="text-white/40 text-[10px]">({entries.length})</span>
                </button>
                
                {isExpanded && (
                  <div className="pl-7 space-y-1 animate-in slide-in-from-top-1 duration-200">
                    {entries.map(([k, v]) => (
                      <div key={k} className="text-xs">
                        <span className="text-white/50">{k}:</span>{' '}
                        <span className="text-white/80">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
