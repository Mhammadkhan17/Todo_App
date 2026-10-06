import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, isValid } from 'date-fns';
import { Task, PriorityOption, TaskFormData, TaskFilter } from '../types';

// Date utilities
export const formatTaskDate = (dateString: string | undefined): string => {
  if (!dateString) return 'No date set';

  try {
    const date = new Date(dateString);
    if (!isValid(date)) return 'Invalid date';

    return format(date, 'MMM dd, yyyy');
  } catch {
    return 'Invalid date';
  }
};

export const formatTaskTimeAgo = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    if (!isValid(date)) return 'Unknown time';

    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return 'Unknown time';
  }
};

export const isOverdue = (dueDate: string | undefined): boolean => {
  if (!dueDate) return false;

  try {
    const due = new Date(dueDate);
    const now = new Date();
    return due < now && due.toDateString() !== now.toDateString();
  } catch {
    return false;
  }
};

export const getPriorityColor = (priority: string): string => {
  switch (priority.toLowerCase()) {
    case 'high':
      return 'text-red-600 bg-red-100';
    case 'medium':
      return 'text-yellow-600 bg-yellow-100';
    case 'low':
      return 'text-green-600 bg-green-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

export const getPriorityOptions = (): PriorityOption[] => [
  { value: 'low', label: 'Low', color: 'text-green-600 bg-green-100' },
  { value: 'medium', label: 'Medium', color: 'text-yellow-600 bg-yellow-100' },
  { value: 'high', label: 'High', color: 'text-red-600 bg-red-100' },
];

// Task utilities
export const getTaskStatus = (task: Task): string => {
  if (task.completed) return 'Completed';
  if (isOverdue(task.due_date)) return 'Overdue';
  return 'In Progress';
};

export const getTaskStatusColor = (task: Task): string => {
  if (task.completed) return 'text-green-600 bg-green-100';
  if (isOverdue(task.due_date)) return 'text-red-600 bg-red-100';
  return 'text-blue-600 bg-blue-100';
};

export const filterTasks = (tasks: Task[], filters: TaskFilter): Task[] => {
  return tasks.filter(task => {
    // Priority filter
    if (filters.priority && task.priority !== filters.priority) {
      return false;
    }

    // Completion filter
    if (filters.completed !== undefined && task.completed !== filters.completed) {
      return false;
    }

    // Date range filter
    if (filters.due_date?.start || filters.due_date?.end) {
      if (!task.due_date) return false;

      const taskDate = new Date(task.due_date);
      if (filters.due_date.start) {
        const startDate = new Date(filters.due_date.start);
        if (taskDate < startDate) return false;
      }
      if (filters.due_date.end) {
        const endDate = new Date(filters.due_date.end);
        if (taskDate > endDate) return false;
      }
    }

    // Search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      const titleMatch = task.title.toLowerCase().includes(searchLower);
      const descriptionMatch = task.description?.toLowerCase().includes(searchLower);
      if (!titleMatch && !descriptionMatch) return false;
    }

    return true;
  });
};

// Form validation utilities
export const validateTaskForm = (data: TaskFormData): string[] => {
  const errors: string[] = [];

  if (!data.title.trim()) {
    errors.push('Title is required');
  }

  if (data.title.length > 200) {
    errors.push('Title must be less than 200 characters');
  }

  if (data.description && data.description.length > 1000) {
    errors.push('Description must be less than 1000 characters');
  }

  if (!['low', 'medium', 'high'].includes(data.priority)) {
    errors.push('Invalid priority level');
  }

  if (data.due_date) {
    const dueDate = new Date(data.due_date);
    if (!isValid(dueDate)) {
      errors.push('Invalid due date');
    }
  }

  return errors;
};

// Local storage utilities
export const localStorageKeys = {
  authToken: 'auth_token',
  user: 'user_data',
  preferences: 'user_preferences',
};

export const saveToLocalStorage = <T>(key: string, data: T): void => {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (error) {
    console.warn('Failed to save to localStorage:', error);
  }
};

export const getFromLocalStorage = <T>(key: string, defaultValue: T): T => {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.warn('Failed to read from localStorage:', error);
    return defaultValue;
  }
};

export const removeFromLocalStorage = (key: string): void => {
  try {
    localStorage.removeItem(key);
  } catch (error) {
    console.warn('Failed to remove from localStorage:', error);
  }
};

// Theme utilities
export const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'light';
};

export const applyTheme = (theme: 'light' | 'dark'): void => {
  if (typeof window !== 'undefined') {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
  }
};

/**
 * Gets the base URL for the application based on the environment
 * @returns The base URL string
 */
export function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    // Browser environment
    return window.location.origin;
  }

  // Server environment
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}`;
  }

  if (process.env.NEXT_PUBLIC_BASE_URL) {
    return process.env.NEXT_PUBLIC_BASE_URL;
  }

  // Default to localhost in development
  return 'http://localhost:3000';
}

/**
 * Gets the backend API URL
 * @returns The backend API URL string
 */
export function getBackendUrl(): string {
  return process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
}

// Utility function for merging class names
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}