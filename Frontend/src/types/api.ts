// API Response Types
export interface UploadResponse {
    status: string;
    filename: string;
    size_kb: number;
    message: string;
}

export interface AnalysisResponse {
    status: string;
    filename: string;
    analysis: {
        content_type: string;
        page_count: number;
        has_tables: boolean;
        text_preview: string;
    };
}

// Conversion status types
export type ConversionStatus =
    | 'idle'
    | 'uploading'
    | 'processing'
    | 'success'
    | 'error';

export interface ConversionState {
    status: ConversionStatus;
    progress: number;
    message: string;
    filename?: string;
    downloadUrl?: string;
    error?: string;
}
