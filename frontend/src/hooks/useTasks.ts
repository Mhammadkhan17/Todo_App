'use client';

import { useState, useCallback } from 'react';
import { Task, TaskQuery, CreateTaskData, UpdateTaskData, TaskStatistics } from '@/types';
import { taskApi, getApiErrorMessage } from '@/lib/api';

interface UseTasksReturn {
  tasks: Task[];
  statistics: TaskStatistics | null;
  isLoading: boolean;
  error: string | null;
  fetchTasks: (userId: number, filters?: TaskQuery) => Promise<void>;
  fetchStatistics: (userId: number) => Promise<void>;
  refreshData: (userId: number) => Promise<void>;
  createTask: (userId: number, data: CreateTaskData) => Promise<void>;
  updateTask: (userId: number, id: number, data: UpdateTaskData) => Promise<void>;
  deleteTask: (userId: number, id: number) => Promise<void>;
  toggleTask: (userId: number, id: number) => Promise<void>;
  clearError: () => void;
}

export function useTasks(): UseTasksReturn {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statistics, setStatistics] = useState<TaskStatistics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async (userId: number, filters?: TaskQuery) => {
    setIsLoading(true);
    setError(null);

    try {
      const fetchedTasks = await taskApi.getTasks(userId, filters);
      setTasks(fetchedTasks);
    } catch (error) {
      setError(getApiErrorMessage(error, 'Failed to fetch tasks'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Force refresh of all data
  const refreshData = async (userId: number) => {
    setIsLoading(true);
    try {
      // Fetch both tasks and statistics
      const [tasksData, statsData] = await Promise.all([
        taskApi.getTasks(userId),
        taskApi.getStatistics(userId)
      ]);

      setTasks(tasksData);
      setStatistics(statsData);
    } catch (error) {
      setError(getApiErrorMessage(error, 'Failed to refresh data'));
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStatistics = useCallback(async (userId: number) => {
    setIsLoading(true);
    setError(null);

    try {
      const stats = await taskApi.getStatistics(userId);
      setStatistics(stats);
    } catch (error) {
      setError(getApiErrorMessage(error, 'Failed to fetch statistics'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createTask = async (userId: number, data: CreateTaskData) => {
    setIsLoading(true);
    setError(null);

    try {
      const newTask = await taskApi.createTask(userId, data);
      setTasks((prev) => [newTask, ...prev]);
    } catch (error) {
      setError(getApiErrorMessage(error, 'Failed to create task'));
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateTask = async (userId: number, id: number, data: UpdateTaskData) => {
    setIsLoading(true);
    setError(null);

    try {
      const updatedTask = await taskApi.updateTask(userId, id, data);
      setTasks((prev) =>
        prev.map((task) => (task.id === id ? updatedTask : task))
      );
    } catch (error) {
      setError(getApiErrorMessage(error, 'Failed to update task'));
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const deleteTask = async (userId: number, id: number) => {
    setIsLoading(true);
    setError(null);

    try {
      await taskApi.deleteTask(userId, id);
      setTasks((prev) => prev.filter((task) => task.id !== id));
    } catch (error) {
      setError(getApiErrorMessage(error, 'Failed to delete task'));
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTask = async (userId: number, id: number) => {
    setIsLoading(true);
    setError(null);

    try {
      const toggledTask = await taskApi.toggleTask(userId, id);
      setTasks((prev) =>
        prev.map((task) => (task.id === id ? toggledTask : task))
      );
    } catch (error) {
      setError(getApiErrorMessage(error, 'Failed to toggle task'));
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  // Statistics need to be fetched with user context

  return {
    tasks,
    statistics,
    isLoading,
    error,
    fetchTasks,
    fetchStatistics,
    refreshData,
    createTask,
    updateTask,
    deleteTask,
    toggleTask,
    clearError,
  };
}