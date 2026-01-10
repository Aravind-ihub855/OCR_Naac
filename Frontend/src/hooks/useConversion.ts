import { useState, useCallback, useRef } from 'react';
import * as XLSX from 'xlsx';
import { convertToExcel, analyzePdf, downloadBlob } from '../services'; // Added analyzePdf
import type { ConversionState, AnalysisResponse } from '../types'; // Added AnalysisResponse
import type { SheetData } from '../components';

const initialState: ConversionState = {
    status: 'idle',
    progress: 0,
    message: '',
};

export function useConversion() {
    const [state, setState] = useState<ConversionState>(initialState);
    const [previewData, setPreviewData] = useState<SheetData[]>([]);
    const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null); // New State
    const blobRef = useRef<Blob | null>(null);
    const filenameRef = useRef<string>('');

    const updateState = useCallback((updates: Partial<ConversionState>) => {
        setState(prev => ({ ...prev, ...updates }));
    }, []);

    // ... (keep parseExcelForPreview as is)
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
                const limitedData = jsonData.slice(0, 100) as string[][];
                sheets.push({ name: sheetName, data: limitedData });
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
        setAnalysisData(null); // Reset analysis

        try {
            updateState({
                status: 'uploading',
                progress: 10,
                message: `Uploading ${file.name}...`,
                filename: file.name,
            });

            // Start Progress Simulation
            const progressInterval = setInterval(() => {
                setState(prev => {
                    if (prev.progress < 40) return { ...prev, progress: prev.progress + 5 };
                    return prev;
                });
            }, 200);

            setTimeout(() => {
                updateState({
                    status: 'processing',
                    progress: 40,
                    message: 'Extracting Logos, Signatures & Tables...',
                });
            }, 1000);

            // PARALLEL EXECUTION: Analyze (JSON) + Convert (Excel)
            // We want the JSON for the UI immediately
            const [analysisResult, blob] = await Promise.all([
                analyzePdf(file).catch(err => {
                    console.error("Analysis failed", err);
                    return null;
                }),
                convertToExcel(file, (progress) => {
                    // Map upload progress (0-100) to overall progress (50-90)
                    if (progress > 0) {
                        updateState({ progress: 50 + Math.floor(progress * 0.4) });
                    }
                })
            ]);

            clearInterval(progressInterval);

            if (!blob) throw new Error("Conversion failed to return a file.");

            blobRef.current = blob;

            // Set Analysis Data (Master Report source)
            if (analysisResult) {
                // @ts-ignore - The API response might slightly differ, trusting the new type
                setAnalysisData(analysisResult);
            }

            // Parse Excel for Preview (Legacy Table View)
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
        setAnalysisData(null);
        blobRef.current = null;
        filenameRef.current = '';
    }, []);

    return {
        ...state,
        previewData,
        analysisData, // Export new state
        convert,
        download,
        reset,
    };
}
