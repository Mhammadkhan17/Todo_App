import axios, { AxiosInstance, isAxiosError } from 'axios';
import { ApiResponse, AuthResponse, User, Task, TaskStatistics, TaskQuery, CreateTaskData, UpdateTaskData } from '../types';
import { getBackendUrl } from './utils';

// Base API configuration - point to backend API
const API_BASE_URL = `${getBackendUrl()}/api`;

class ApiClient {
  public client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to include auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle auth errors
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access - clear auth data and redirect
          try {
            // Clear auth data from localStorage
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user');

            // Redirect to login page
            if (typeof window !== 'undefined') {
              window.location.href = '/auth/login';
            }
          } catch (signOutError) {
            console.error('Sign out error:', signOutError);
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth methods
  async login(credentials: { email: string; password: string }): Promise<AuthResponse> {
    try {
      const response = await this.client.post('/token', {
        username: credentials.email,
        password: credentials.password,
      });

      const { access_token } = response.data;

      // Store the token in localStorage
      localStorage.setItem('auth_token', access_token);

      // Get user info
      const userResponse = await this.client.get('/me', {
        headers: {
          'Authorization': `Bearer ${access_token}`,
        }
      });

      const userData = userResponse.data;

      // Store user info
      localStorage.setItem('user', JSON.stringify(userData));

      return {
        user: {
          id: userData.id,
          email: userData.email,
          username: userData.username || userData.email.split('@')[0],
          name: userData.full_name || userData.name || userData.username,
          avatar: userData.image || userData.avatar || userData.picture || null,
          is_active: userData.is_active ?? true,
          email_verified: userData.email_verified ?? false,
          created_at: userData.created_at || new Date().toISOString(),
          updated_at: userData.updated_at || new Date().toISOString()
        },
        access_token: access_token,
        success: true
      };
    } catch (error) {
      if (isAxiosError(error)) {
        if (error.response) {
          // Server responded with error status
          const data = error.response.data as { detail?: string; message?: string } | undefined;
          if (data?.detail) {
            throw new Error(data.detail);
          } else if (data?.message) {
            throw new Error(data.message);
          } else {
            throw new Error(`Login failed with status ${error.response.status}`);
          }
        } else if (error.request) {
          // Request was made but no response received
          throw new Error('Network error: Unable to reach the server');
        }
      }
      // Something else happened
      throw new Error(error instanceof Error && error.message ? error.message : 'Login failed');
    }
  }

  async register(data: { email: string; password: string; name?: string }): Promise<AuthResponse> {
    try {
      await this.client.post('/register', {
        email: data.email,
        password: data.password,
        username: data.name || data.email.split('@')[0],
        full_name: data.name || data.email.split('@')[0],
      });

      // Auto-login after successful registration
      return await this.login({
        email: data.email,
        password: data.password,
      });
    } catch (error) {
      if (isAxiosError(error)) {
        if (error.response) {
          // Server responded with error status
          const data = error.response.data as { detail?: string; message?: string } | undefined;
          if (data?.detail) {
            throw new Error(data.detail);
          } else if (data?.message) {
            throw new Error(data.message);
          } else {
            throw new Error(`Registration failed with status ${error.response.status}`);
          }
        } else if (error.request) {
          // Request was made but no response received
          throw new Error('Network error: Unable to reach the server');
        }
      }
      // Something else happened
      throw new Error(error instanceof Error && error.message ? error.message : 'Registration failed');
    }
  }

  async logout(): Promise<void> {
    try {
      // Clear auth data from localStorage
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');

      // Redirect to login page
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  async refreshToken(): Promise<AuthResponse> {
    // For now, just return current user data
    // In a real implementation, you'd make a call to refresh the token
    try {
      const user = await this.getCurrentUser();
      const token = localStorage.getItem('auth_token');
      return {
        user: user,
        access_token: token || '',
        success: true
      };
    } catch {
      throw new Error('Token refresh failed');
    }
  }

  async requestPasswordReset(email: string): Promise<ApiResponse> {
    try {
      await this.client.post('/auth/request-password-reset', { email });
      return { success: true, message: 'Password reset email sent' };
    } catch (error) {
      if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Password reset request failed');
    }
  }

  async resetPassword(token: string, password: string): Promise<ApiResponse> {
    try {
      await this.client.post('/auth/reset-password', { token, password });
      return { success: true, message: 'Password reset successfully' };
    } catch (error) {
      if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Password reset failed');
    }
  }

  // User methods
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/me');
    const userData = response.data;

    return {
      id: userData.id,
      email: userData.email,
      username: userData.username || userData.email.split('@')[0],
      name: userData.full_name || userData.name || userData.username,
      avatar: userData.image || userData.avatar || userData.picture || null,
      is_active: userData.is_active ?? true,
      email_verified: userData.email_verified ?? false,
      created_at: userData.created_at || new Date().toISOString(),
      updated_at: userData.updated_at || new Date().toISOString()
    };
  }

  // Task methods
  async getTasks(userId: number, params?: TaskQuery): Promise<Task[]> {
    const response = await this.client.get<{tasks: Task[], total: number, page: number, size: number, total_pages: number}>(`/${userId}/tasks`, { params });

    // Transform priorities from uppercase (backend) to lowercase (frontend)
    // and status to completed boolean for frontend compatibility
    return response.data.tasks?.map(task => ({
      ...task,
      priority: task.priority?.toLowerCase() as 'low' | 'medium' | 'high',
      completed: task.status === 'COMPLETED'
    })) || [];
  }

  async getTask(userId: number, id: number): Promise<Task> {
    const response = await this.client.get<Task>(`/${userId}/tasks/${id}`);

    // Transform priority from uppercase (backend) to lowercase (frontend)
    // and status to completed boolean for frontend compatibility
    const taskData = response.data;
    return {
      ...taskData,
      priority: taskData.priority.toLowerCase() as 'low' | 'medium' | 'high',
      completed: taskData.status === 'COMPLETED'
    };
  }

  async createTask(userId: number, data: CreateTaskData): Promise<Task> {
    // Transform priority from lowercase to uppercase to match backend enum
    const transformedData = {
      ...data,
      priority: data.priority.toUpperCase()
    };

    const response = await this.client.post<Task>(`/${userId}/tasks`, transformedData);

    // Transform priority back to lowercase to match frontend types
    // and status to completed boolean for frontend compatibility
    const taskData = response.data;
    return {
      ...taskData,
      priority: taskData.priority.toLowerCase() as 'low' | 'medium' | 'high',
      completed: taskData.status === 'COMPLETED'
    };
  }

  async updateTask(userId: number, id: number, data: UpdateTaskData): Promise<Task> {
    // Transform priority from lowercase to uppercase to match backend enum if priority is provided
    const transformedData = {
      ...data,
      ...(data.priority ? { priority: data.priority.toUpperCase() } : {}),
    };

    const response = await this.client.put<Task>(`/${userId}/tasks/${id}`, transformedData);

    // Transform priority from uppercase (backend) to lowercase (frontend)
    // and status to completed boolean for frontend compatibility
    const taskData = response.data;
    return {
      ...taskData,
      priority: taskData.priority.toLowerCase() as 'low' | 'medium' | 'high',
      completed: taskData.status === 'COMPLETED'
    };
  }

  async deleteTask(userId: number, id: number): Promise<void> {
    await this.client.delete(`/${userId}/tasks/${id}`);
  }

  async toggleTask(userId: number, id: number): Promise<Task> {
    await this.client.patch(`/${userId}/tasks/${id}/complete`);

    // Get the updated task details to return a complete Task object
    // The toggle endpoint returns toggle info, but we need full task details
    return await this.getTask(userId, id);
  }

  // Statistics methods
  async getStatistics(userId: number): Promise<TaskStatistics> {
    const response = await this.client.get(`/${userId}/stats`);
    const userData = response.data;

    // Map the user stats to TaskStatistics format
    return {
      total: userData.total_tasks || 0,
      completed: userData.completed_tasks || 0,
      pending: userData.active_tasks || 0,
      in_progress: 0, // Not available from user stats
      overdue: userData.overdue_tasks || 0, // Get the overdue count from backend
      priority_breakdown: {
        low: userData.priority_breakdown?.low || 0, // Get low priority from backend
        medium: userData.priority_breakdown?.medium || 0, // Get medium priority from backend
        high: userData.priority_breakdown?.high || 0 // Get high priority from backend
      }
    };
  }

  // Utility methods
  private getAuthToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  private setAuthToken(token: string): void {
    localStorage.setItem('auth_token', token);
  }

  private clearAuthToken(): void {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Extract a human-readable message from an API error, with a fallback
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    const data = error.response?.data as { error?: unknown; detail?: unknown } | undefined;
    if (typeof data?.error === 'string') return data.error;
    if (typeof data?.detail === 'string') return data.detail;
  }
  return fallback;
}

// Export typed methods for convenience
export const authApi = {
  login: (credentials: { email: string; password: string }) => apiClient.login(credentials),
  register: (data: { email: string; password: string; name?: string }) => apiClient.register(data),
  logout: () => apiClient.logout(),
  refreshToken: () => apiClient.refreshToken(),
  requestPasswordReset: (email: string) => apiClient.requestPasswordReset(email),
  resetPassword: (token: string, password: string) => apiClient.resetPassword(token, password),
  getCurrentUser: () => apiClient.getCurrentUser(),
};

export const taskApi = {
  getTasks: (userId: number, params?: TaskQuery) => apiClient.getTasks(userId, params),
  getTask: (userId: number, id: number) => apiClient.getTask(userId, id),
  createTask: (userId: number, data: CreateTaskData) => apiClient.createTask(userId, data),
  updateTask: (userId: number, id: number, data: UpdateTaskData) => apiClient.updateTask(userId, id, data),
  deleteTask: (userId: number, id: number) => apiClient.deleteTask(userId, id),
  toggleTask: (userId: number, id: number) => apiClient.toggleTask(userId, id),
  getStatistics: (userId: number) => apiClient.getStatistics(userId),
};

export default apiClient;