import { CheckCircle, Download, AlertTriangle, Loader2 } from 'lucide-react';
import type { ConversionStatus } from '../types';

interface ResultCardProps {
    status: ConversionStatus;
    filename?: string;
    message: string;
    onDownload?: () => void;
    onReset?: () => void;
}

export function ResultCard({
    status,
    filename,
    message,
    onDownload,
    onReset
}: ResultCardProps) {
    if (status === 'idle') return null;

    const getStatusConfig = () => {
        switch (status) {
            case 'success':
                return {
                    icon: CheckCircle,
                    iconColor: 'text-green-600',
                    bgColor: 'bg-green-50',
                    borderColor: 'border-green-200',
                    title: 'Done!',
                };
            case 'error':
                return {
                    icon: AlertTriangle,
                    iconColor: 'text-red-600',
                    bgColor: 'bg-red-50',
                    borderColor: 'border-red-200',
                    title: 'Failed',
                };
            default:
                return {
                    icon: Loader2,
                    iconColor: 'text-gray-600',
                    bgColor: 'bg-gray-50',
                    borderColor: 'border-gray-200',
                    title: 'Processing...',
                };
        }
    };

    const config = getStatusConfig();
    const Icon = config.icon;

    return (
        <div className={`w-full p-6 rounded-xl border ${config.bgColor} ${config.borderColor}`}>
            <div className="flex items-start gap-4">
                <div className={`p-3 rounded-lg ${config.bgColor}`}>
                    <Icon className={`w-6 h-6 ${config.iconColor} ${status === 'processing' || status === 'uploading' ? 'animate-spin' : ''}`} />
                </div>

                <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900">{config.title}</h3>
                    <p className="text-sm text-gray-500 mt-1">{message}</p>

                    {filename && status === 'success' && (
                        <p className="text-sm text-gray-400 mt-2">
                            <span className="font-mono">{filename.replace('.pdf', '.xlsx')}</span>
                        </p>
                    )}
                </div>

                <div className="flex gap-2">
                    {status === 'success' && onDownload && (
                        <button
                            onClick={onDownload}
                            className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-lg transition-colors"
                        >
                            <Download className="w-4 h-4" />
                            Download
                        </button>
                    )}

                    {(status === 'success' || status === 'error') && onReset && (
                        <button
                            onClick={onReset}
                            className="px-5 py-2.5 text-gray-600 hover:text-gray-900 border border-gray-300 hover:border-gray-400 rounded-lg transition-colors"
                        >
                            New File
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
