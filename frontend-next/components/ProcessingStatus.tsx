import { Loader2 } from 'lucide-react';

interface ProcessingStatusProps {
  message: string;
}

export function ProcessingStatus({ message }: ProcessingStatusProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-white/50 backdrop-blur-sm rounded-full border border-white/60 shadow-sm max-w-fit">
      <Loader2 className="w-4 h-4 text-purple-600 animate-spin" />
      <span className="text-sm text-gray-700">{message}</span>
    </div>
  );
}
