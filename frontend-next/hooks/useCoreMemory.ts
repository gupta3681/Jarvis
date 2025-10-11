import { useEffect, useState } from 'react';

export interface CoreMemoryData {
  identity: Record<string, any>;
  work: Record<string, any>;
  preferences: Record<string, any>;
  health: Record<string, any>;
  relationships: Record<string, any>;
  context: Record<string, any>;
}

interface CoreMemoryResponse {
  success: boolean;
  user_id: string;
  core_memory: CoreMemoryData;
  error?: string;
}

export function useCoreMemory(userId: string = 'default_user') {
  const [coreMemory, setCoreMemory] = useState<CoreMemoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCoreMemory = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/api/core-memory?user_id=${userId}`);
      const data: CoreMemoryResponse = await response.json();

      if (data.success) {
        setCoreMemory(data.core_memory);
        setError(null);
      } else {
        setError(data.error || 'Failed to fetch core memory');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCoreMemory();
  }, [userId]);

  return {
    coreMemory,
    loading,
    error,
    refetch: fetchCoreMemory,
  };
}
