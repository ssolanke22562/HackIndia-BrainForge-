/**
 * API Configuration helper for SecondSelf
 * In development (localhost): uses relative paths which Vite proxies to http://127.0.0.1:8000.
 * In production (deployed on Vercel/custom domain): uses direct backend URL to avoid Vercel payload limits & rewrite dropouts.
 */
const getBaseUrl = (): string => {
  const envUrl = (import.meta as any).env?.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  
  // If running in browser and NOT localhost/127.0.0.1, default to direct Render backend
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.') || hostname.startsWith('10.');
    if (!isLocal) {
      return 'https://hackindia-brainforge-3.onrender.com';
    }
  }
  
  return '';
};

export const API_BASE_URL: string = getBaseUrl();

export const apiUrl = (endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

export default apiUrl;
