interface ProgressBarProps {
    progress: number;
    status: string;
}

export function ProgressBar({ progress, status }: ProgressBarProps) {
    return (
        <div className="w-full space-y-3">
            <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-600">{status}</p>
                <span className="text-sm font-mono text-gray-900">{progress}%</span>
            </div>

            <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gray-900 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${progress}%` }}
                />
            </div>

            {progress > 0 && progress < 100 && (
                <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-xs text-gray-400">Processing...</span>
                </div>
            )}
        </div>
    );
}
