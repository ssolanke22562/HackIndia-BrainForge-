/**
 * API Configuration helper for SecondSelf
 * Supports VITE_API_BASE_URL (for direct cross-origin calls in production)
 * and fallback relative paths (for local Vite dev proxy and Vercel rewrites).
 */
export const API_BASE_URL: string = (
  (import.meta as any).env?.VITE_API_BASE_URL || ''
).replace(/\/+$/, '');

export const apiUrl = (endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

export default apiUrl;
