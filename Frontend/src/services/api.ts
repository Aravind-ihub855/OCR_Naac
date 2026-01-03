import axios from 'axios';
import { API_ENDPOINTS } from '../config/api';
import type { UploadResponse, AnalysisResponse } from '../types';

// Create axios instance with default config
const api = axios.create({
    timeout: 300000, // 5 minutes for large PDFs
});

/**
 * Upload PDF for quick analysis
 */
export async function uploadPdf(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<UploadResponse>(API_ENDPOINTS.upload, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
}

/**
 * Analyze PDF structure
 */
export async function analyzePdf(file: File): Promise<AnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<AnalysisResponse>(API_ENDPOINTS.analyze, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
}

/**
 * Convert PDF to Excel - returns blob for download
 */
export async function convertToExcel(
    file: File,
    onProgress?: (progress: number) => void
): Promise<Blob> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(API_ENDPOINTS.convert, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob',
        onUploadProgress: (progressEvent) => {
            if (progressEvent.total && onProgress) {
                const progress = Math.round((progressEvent.loaded * 50) / progressEvent.total);
                onProgress(progress);
            }
        },
        onDownloadProgress: (progressEvent) => {
            if (progressEvent.total && onProgress) {
                const progress = 50 + Math.round((progressEvent.loaded * 50) / progressEvent.total);
                onProgress(progress);
            }
        },
    });

    return response.data;
}

/**
 * Download blob as file
 */
export function downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}
