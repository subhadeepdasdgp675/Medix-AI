// Point to active backend (Railway in production, or localhost:8080 in dev)
export const API_BASE = import.meta.env.VITE_API_URL || ((typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))
  ? 'http://localhost:8080'
  : 'https://medix-ai-production-eca9.up.railway.app');


export function getAuthToken(): string | null {
  return localStorage.getItem('medix_auth_token');
}

export function setAuthToken(token: string) {
  localStorage.setItem('medix_auth_token', token);
}

export function clearAuth() {
  localStorage.removeItem('medix_auth_token');
  localStorage.removeItem('medix_user');
}

export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  if (response.status === 401 && window.location.pathname !== '/login') {
    // If unauthorized, clear auth and redirect to login
    clearAuth();
    window.location.href = '/login';
  }
  
  return response;
}
