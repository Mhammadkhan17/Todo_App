import { getBackendUrl } from './utils';

interface RequestOptions {
  headers?: Record<string, string>;
  credentials?: 'include' | 'omit' | 'same-origin';
  method?: string;
  body?: string;
}

class BetterApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = getBackendUrl();
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const config: RequestInit = {
      credentials: options.credentials || 'include',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(url, config);

    if (!response.ok) {
      if (response.status === 401) {
        // Handle unauthorized access - redirect to login
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
        }
        throw new Error('Unauthorized access');
      }

      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
    }

    // For DELETE requests, don't try to parse JSON response
    if (response.status === 204 || endpoint.includes('/delete') || config.method === 'DELETE') {
      return undefined as T;
    }

    return await response.json();
  }

  get<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  post<T>(endpoint: string, data?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  put<T>(endpoint: string, data: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  patch<T>(endpoint: string, data: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  delete<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

// Create singleton instance
export const apiClient = new BetterApiClient();

// Export for convenience
export default apiClient;