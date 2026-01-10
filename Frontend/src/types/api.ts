// API Response Types
export interface UploadResponse {
    status: string;
    filename: string;
    size_kb: number;
    message: string;
}

export interface PageElement {
    type: 'logo' | 'signature' | 'metadata' | 'text_block' | 'heading' | 'table';
    order: number;
    // Common fields
    content?: string;
    position?: string;
    // Signature fields
    signer_name?: string;
    designation?: string;
    // Metadata fields
    key?: string;
    value?: string;
    // Table fields
    table_name?: string;
    table_heading?: string; // Added missing field
    rows?: any[];
    columns?: any[];
}

export interface AnalysisResponse {
    status: string;
    filename: string;
    // The structure returned by extractor.py
    tables: any[];
    metadata: any;
    page_elements: PageElement[];
    processing_notes?: string[];
    // Legacy field if still present
    analysis?: {
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
