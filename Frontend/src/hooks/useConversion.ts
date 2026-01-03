import { useState, useCallback, useRef } from 'react';
import { convertToExcel, downloadBlob } from '../services';
import type { ConversionState, ConversionStatus } from '../types';

const initialState: ConversionState = {
    status: 'idle',
    progress: 0,
    message: '',
};

export function useConversion() {
    const [state, setState] = useState<ConversionState>(initialState);
    const blobRef = useRef<Blob | null>(null);
    const filenameRef = useRef<string>('');

    const updateState = useCallback((updates: Partial<ConversionState>) => {
        setState(prev => ({ ...prev, ...updates }));
    }, []);

    const convert = useCallback(async (file: File) => {
        filenameRef.current = file.name;
        blobRef.current = null;

        try {
            // Start upload
            updateState({
                status: 'uploading',
                progress: 10,
                message: `Uploading ${file.name}...`,
                filename: file.name,
            });

            // Simulate progress for better UX
            const progressInterval = setInterval(() => {
                setState(prev => {
                    if (prev.progress < 40) {
                        return { ...prev, progress: prev.progress + 5 };
                    }
                    return prev;
                });
            }, 200);

            // Processing phase
            setTimeout(() => {
                updateState({
                    status: 'processing',
                    progress: 50,
                    message: 'AI is extracting tables from your document...',
                });
            }, 1000);

            // Call API
            const blob = await convertToExcel(file, (progress) => {
                if (progress > 50) {
                    updateState({ progress });
                }
            });

            clearInterval(progressInterval);

            // Success
            blobRef.current = blob;
            updateState({
                status: 'success',
                progress: 100,
                message: 'Your Excel file is ready for download!',
            });

        } catch (error) {
            updateState({
                status: 'error',
                progress: 0,
                message: error instanceof Error ? error.message : 'Conversion failed. Please try again.',
                error: String(error),
            });
        }
    }, [updateState]);

    const download = useCallback(() => {
        if (blobRef.current && filenameRef.current) {
            const excelFilename = filenameRef.current.replace(/\.pdf$/i, '.xlsx');
            downloadBlob(blobRef.current, excelFilename);
        }
    }, []);

    const reset = useCallback(() => {
        setState(initialState);
        blobRef.current = null;
        filenameRef.current = '';
    }, []);

    return {
        ...state,
        convert,
        download,
        reset,
    };
}
