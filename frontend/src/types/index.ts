// User types
export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
  name?: string; // For backward compatibility
  avatar?: string | null; // For backward compatibility
}

// Task types
export interface Task {
  id: number;
  user_id: number;
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
  due_date?: string;
  completed: boolean;
  status?: string; // For backend compatibility
  created_at: string;
  updated_at: string;
}

export interface CreateTaskData {
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
  due_date?: string;
}

export interface UpdateTaskData {
  title?: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high';
  due_date?: string;
  completed?: boolean;
}

// Statistics types
export interface TaskStatistics {
  total: number;
  completed: number;
  pending: number;
  in_progress: number;
  overdue: number;
  priority_breakdown: {
    low: number;
    medium: number;
    high: number;
  };
}

// API response types
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface AuthResponse {
  success: boolean;
  user: User;
  access_token: string;
  message?: string;
  error?: string;
}

// Form types
export interface TaskFormData {
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
  due_date?: string;
}

// Filter and query types
export interface TaskFilter {
  priority?: 'low' | 'medium' | 'high';
  completed?: boolean | 'overdue';
  due_date?: {
    start?: string;
    end?: string;
  };
  search?: string;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
  order_by?: 'created_at' | 'updated_at' | 'due_date' | 'priority';
  order_direction?: 'asc' | 'desc';
}

export interface TaskQuery extends TaskFilter, PaginationParams {}

export interface TaskItemProps {
  task: Task;
  onToggle?: (id: number) => void;
  onEdit?: (task: Task) => void;
  onDelete?: (id: number) => void;
}

export interface TaskListProps {
  tasks: Task[];
  isLoading?: boolean;
  onTaskAction?: (action: 'toggle' | 'edit' | 'delete', task: Task) => void;
}

// Priority type for display
export interface PriorityOption {
  value: 'low' | 'medium' | 'high';
  label: string;
  color: string;
}