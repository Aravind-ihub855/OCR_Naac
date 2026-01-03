import { useState, useEffect } from 'react';
import { API_ENDPOINTS } from '../config/api';

export function useBackendStatus() {
    const [isConnected, setIsConnected] = useState(false);
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        const check = async () => {
            try {
                const response = await fetch(API_ENDPOINTS.health);
                setIsConnected(response.ok);
            } catch {
                setIsConnected(false);
            } finally {
                setIsChecking(false);
            }
        };

        check();

        // Check every 30 seconds
        const interval = setInterval(check, 30000);
        return () => clearInterval(interval);
    }, []);

    return { isConnected, isChecking };
}
