import { useState, useCallback, useRef } from 'react';
import * as XLSX from 'xlsx';
import { convertToExcel, downloadBlob } from '../services';
import type { ConversionState } from '../types';
import type { SheetData } from '../components';

const initialState: ConversionState = {
    status: 'idle',
    progress: 0,
    message: '',
};

export function useConversion() {
    const [state, setState] = useState<ConversionState>(initialState);
    const [previewData, setPreviewData] = useState<SheetData[]>([]);
    const blobRef = useRef<Blob | null>(null);
    const filenameRef = useRef<string>('');

    const updateState = useCallback((updates: Partial<ConversionState>) => {
        setState(prev => ({ ...prev, ...updates }));
    }, []);

    const parseExcelForPreview = async (blob: Blob): Promise<SheetData[]> => {
        try {
            const arrayBuffer = await blob.arrayBuffer();
            const workbook = XLSX.read(arrayBuffer, { type: 'array' });

            const sheets: SheetData[] = [];

            for (const sheetName of workbook.SheetNames) {
                const worksheet = workbook.Sheets[sheetName];
                const jsonData = XLSX.utils.sheet_to_json<string[]>(worksheet, {
                    header: 1,
                    defval: ''
                });

                // Limit to first 100 rows for preview
                const limitedData = jsonData.slice(0, 100) as string[][];

                sheets.push({
                    name: sheetName,
                    data: limitedData
                });
            }

            return sheets;
        } catch (error) {
            console.error('Failed to parse Excel for preview:', error);
            return [];
        }
    };

    const convert = useCallback(async (file: File) => {
        filenameRef.current = file.name;
        blobRef.current = null;
        setPreviewData([]);

        try {
            updateState({
                status: 'uploading',
                progress: 10,
                message: `Uploading ${file.name}...`,
                filename: file.name,
            });

            const progressInterval = setInterval(() => {
                setState(prev => {
                    if (prev.progress < 40) {
                        return { ...prev, progress: prev.progress + 5 };
                    }
                    return prev;
                });
            }, 200);

            setTimeout(() => {
                updateState({
                    status: 'processing',
                    progress: 50,
                    message: 'Extracting data with AI...',
                });
            }, 1000);

            const blob = await convertToExcel(file, (progress) => {
                if (progress > 50) {
                    updateState({ progress });
                }
            });

            clearInterval(progressInterval);
            blobRef.current = blob;

            // Parse Excel for preview
            const sheets = await parseExcelForPreview(blob);
            setPreviewData(sheets);

            updateState({
                status: 'success',
                progress: 100,
                message: 'Extraction complete!',
            });

        } catch (error) {
            updateState({
                status: 'error',
                progress: 0,
                message: error instanceof Error ? error.message : 'Conversion failed.',
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
        setPreviewData([]);
        blobRef.current = null;
        filenameRef.current = '';
    }, []);

    return {
        ...state,
        previewData,
        convert,
        download,
        reset,
    };
}
