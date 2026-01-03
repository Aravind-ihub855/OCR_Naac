import React, { useCallback, useState } from 'react';
import { Upload, File, X, AlertCircle } from 'lucide-react';

interface FileUploadProps {
    onFileSelect: (file: File) => void;
    disabled?: boolean;
    accept?: string;
}

export function FileUpload({
    onFileSelect,
    disabled = false,
    accept = '.pdf'
}: FileUploadProps) {
    const [dragActive, setDragActive] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [error, setError] = useState<string | null>(null);

    const validateFile = (file: File): boolean => {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            setError('Only PDF files are accepted');
            return false;
        }
        if (file.size > 50 * 1024 * 1024) {
            setError('File size must be less than 50MB');
            return false;
        }
        setError(null);
        return true;
    };

    const handleFile = useCallback((file: File) => {
        if (validateFile(file)) {
            setSelectedFile(file);
            onFileSelect(file);
        }
    }, [onFileSelect]);

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (disabled) return;

        const files = e.dataTransfer.files;
        if (files && files[0]) {
            handleFile(files[0]);
        }
    }, [disabled, handleFile]);

    const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files[0]) {
            handleFile(files[0]);
        }
    }, [handleFile]);

    const clearFile = useCallback(() => {
        setSelectedFile(null);
        setError(null);
    }, []);

    return (
        <div className="w-full">
            {/* Drop Zone */}
            <div
                className={`
          relative border-2 border-dashed rounded-xl p-8 transition-all duration-300 cursor-pointer
          ${dragActive
                        ? 'border-gray-900 bg-gray-100'
                        : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
                    }
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !disabled && document.getElementById('file-input')?.click()}
            >
                <input
                    id="file-input"
                    type="file"
                    accept={accept}
                    onChange={handleChange}
                    disabled={disabled}
                    className="hidden"
                />

                <div className="flex flex-col items-center justify-center space-y-4">
                    {selectedFile ? (
                        <>
                            <div className="p-4 bg-gray-100 rounded-full">
                                <File className="w-12 h-12 text-gray-700" />
                            </div>
                            <div className="text-center">
                                <p className="text-lg font-semibold text-gray-900">{selectedFile.name}</p>
                                <p className="text-sm text-gray-500">
                                    {(selectedFile.size / 1024).toFixed(1)} KB
                                </p>
                            </div>
                            {!disabled && (
                                <button
                                    onClick={(e) => { e.stopPropagation(); clearFile(); }}
                                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-500 hover:text-red-500 transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                    Remove
                                </button>
                            )}
                        </>
                    ) : (
                        <>
                            <div className={`p-4 rounded-full ${dragActive ? 'bg-gray-200' : 'bg-gray-100'}`}>
                                <Upload className={`w-12 h-12 ${dragActive ? 'text-gray-900' : 'text-gray-400'}`} />
                            </div>
                            <div className="text-center">
                                <p className="text-lg font-medium text-gray-700">
                                    Drop your PDF here, or <span className="text-gray-900 underline">browse</span>
                                </p>
                                <p className="text-sm text-gray-400 mt-1">
                                    PDF files up to 50MB
                                </p>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="flex items-center gap-2 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
                    <p className="text-sm text-red-600">{error}</p>
                </div>
            )}
        </div>
    );
}
