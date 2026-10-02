// Point to active backend port 8080 or deployed backend via VITE_API_URL
export const API_BASE = import.meta.env.VITE_API_URL || ((typeof window !== 'undefined' && window.location.port && window.location.port !== '8080')
  ? 'http://localhost:8080'
  : '');


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
