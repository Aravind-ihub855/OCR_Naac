// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL;

export const API_ENDPOINTS = {
    upload: `${API_BASE_URL}/upload`,
    analyze: `${API_BASE_URL}/analyze-only`,
    convert: `${API_BASE_URL}/convert`,
    health: `${API_BASE_URL}/`,
} as const;
