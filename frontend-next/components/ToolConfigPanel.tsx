'use client';

import { useState, useEffect } from 'react';
import { Settings, ToggleLeft, ToggleRight, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';

interface ToolConfig {
  [key: string]: boolean;
}

// Tool display names and descriptions
const TOOL_INFO: Record<string, { name: string; description: string; category: string }> = {
  core_memory: {
    name: 'Core Memory',
    description: 'Store important facts about you',
    category: 'Memory',
  },
  episodic_memory: {
    name: 'Episodic Memory',
    description: 'Remember experiences and conversations',
    category: 'Memory',
  },
  web_search: {
    name: 'Web Search',
    description: 'Search the internet for information',
    category: 'Utilities',
  },
  calendar: {
    name: 'Calendar',
    description: 'Manage Google Calendar events',
    category: 'Integrations',
  },
  nutrition_handler: {
    name: 'Nutrition',
    description: 'Log food and track nutrition',
    category: 'Handlers',
  },
  workout_handler: {
    name: 'Workout',
    description: 'Log exercises and track workouts',
    category: 'Handlers',
  },
  gmail_handler: {
    name: 'Gmail',
    description: 'Search, read, and send emails',
    category: 'Handlers',
  },
  think_tool: {
    name: 'Think Tool',
    description: 'Internal reasoning capability',
    category: 'Core',
  },
  task_complete: {
    name: 'Task Complete',
    description: 'Signal task completion',
    category: 'Core',
  },
};

// Group tools by category
const CATEGORIES = ['Handlers', 'Integrations', 'Memory', 'Utilities', 'Core'];

export function ToolConfigPanel() {
  const [tools, setTools] = useState<ToolConfig>({});
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch tool config on mount
  useEffect(() => {
    fetchToolConfig();
  }, []);

  const fetchToolConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('http://localhost:8000/api/tool-config');
      const data = await response.json();
      if (data.success) {
        setTools(data.tools);
      } else {
        setError(data.error || 'Failed to fetch config');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const toggleTool = async (toolName: string) => {
    try {
      setUpdating(toolName);
      setError(null);
      
      const newValue = !tools[toolName];
      
      const response = await fetch('http://localhost:8000/api/tool-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_name: toolName, enabled: newValue }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setTools((prev) => ({ ...prev, [toolName]: newValue }));
      } else {
        setError(data.error || 'Failed to update');
      }
    } catch (err) {
      setError('Failed to update tool');
    } finally {
      setUpdating(null);
    }
  };

  const enabledCount = Object.values(tools).filter(Boolean).length;
  const totalCount = Object.keys(tools).length;

  if (loading) {
    return (
      <div className="px-6 py-4">
        <div className="flex items-center gap-2 text-white/50 text-sm">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Loading tools...
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-4">
      {/* Header - Always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-white/70 hover:text-white transition-colors"
      >
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4" />
          <span className="text-sm font-medium">Tools</span>
          <span className="text-xs text-white/50">
            ({enabledCount}/{totalCount})
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-4 space-y-4">
          {error && (
            <div className="text-xs text-red-400 bg-red-400/10 px-3 py-2 rounded-lg">
              {error}
            </div>
          )}

          {CATEGORIES.map((category) => {
            const categoryTools = Object.entries(tools).filter(
              ([key]) => TOOL_INFO[key]?.category === category
            );

            if (categoryTools.length === 0) return null;

            return (
              <div key={category}>
                <h4 className="text-xs text-white/40 uppercase tracking-wider mb-2">
                  {category}
                </h4>
                <div className="space-y-1">
                  {categoryTools.map(([toolName, enabled]) => {
                    const info = TOOL_INFO[toolName];
                    const isUpdating = updating === toolName;

                    return (
                      <button
                        key={toolName}
                        onClick={() => toggleTool(toolName)}
                        disabled={isUpdating}
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-all ${
                          enabled
                            ? 'bg-white/10 hover:bg-white/15'
                            : 'bg-white/5 hover:bg-white/10 opacity-60'
                        } ${isUpdating ? 'opacity-50' : ''}`}
                      >
                        <div className="text-left">
                          <div className="text-sm text-white">
                            {info?.name || toolName}
                          </div>
                          <div className="text-xs text-white/50">
                            {info?.description || ''}
                          </div>
                        </div>
                        <div className="flex-shrink-0 ml-2">
                          {isUpdating ? (
                            <RefreshCw className="w-5 h-5 text-white/50 animate-spin" />
                          ) : enabled ? (
                            <ToggleRight className="w-6 h-6 text-green-400" />
                          ) : (
                            <ToggleLeft className="w-6 h-6 text-white/30" />
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}

          <p className="text-xs text-white/40 text-center pt-2">
            Reconnect after changes
          </p>
        </div>
      )}
    </div>
  );
}
