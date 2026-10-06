'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface TaskFormData {
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
  due_date?: string;
  tags?: string[];
}

interface TaskFormProps {
  onSubmit: (data: TaskFormData) => void;
  onCancel: () => void;
  isLoading?: boolean;
  initialData?: Partial<TaskFormData>;
}

export function LuxuryTaskForm({ onSubmit, onCancel, isLoading, initialData }: TaskFormProps) {
  const [formData, setFormData] = useState<TaskFormData>({
    title: initialData?.title || '',
    description: initialData?.description || '',
    priority: initialData?.priority || 'medium',
    due_date: initialData?.due_date || '',
    tags: initialData?.tags || [],
  });

  const [newTag, setNewTag] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const addTag = () => {
    if (newTag.trim() && !formData.tags?.includes(newTag.trim())) {
      setFormData({
        ...formData,
        tags: [...(formData.tags || []), newTag.trim()]
      });
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setFormData({
      ...formData,
      tags: formData.tags?.filter(tag => tag !== tagToRemove) || []
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && newTag.trim()) {
      e.preventDefault();
      addTag();
    }
  };

  return (
    <motion.form
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      onSubmit={handleSubmit}
      className="space-y-6"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Title */}
        <div className="md:col-span-2 space-y-2">
          <label htmlFor="title" className="block text-[10px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase tracking-[0.2em]">
            OPERATION_TITLE *
          </label>
          <input
            type="text"
            id="title"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="w-full px-4 py-3 bg-stone-50 dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] text-stone-900 dark:text-white text-sm focus:outline-none focus:border-emerald-600/60 transition-colors"
            placeholder="Execute command..."
            required
          />
        </div>

        {/* Description */}
        <div className="md:col-span-2 space-y-2">
          <label htmlFor="description" className="block text-[10px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase tracking-[0.2em]">
            OPERATION_DETAILS
          </label>
          <textarea
            id="description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
            className="w-full px-4 py-3 bg-stone-50 dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] text-stone-900 dark:text-white text-sm focus:outline-none focus:border-emerald-600/60 transition-colors"
            placeholder="Payload description..."
          />
        </div>

        {/* Priority */}
        <div className="space-y-2">
          <label className="block text-[10px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase tracking-[0.2em]">
            CRITICALITY_LEVEL
          </label>
          <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Priority">
            {(['low', 'medium', 'high'] as const).map((priority) => (
              <button
                key={priority}
                type="button"
                role="radio"
                aria-checked={formData.priority === priority}
                onClick={() => setFormData({ ...formData, priority })}
                className={cn(
                  "min-h-11 px-2 rounded-[4px] border text-[10px] font-mono uppercase tracking-widest transition-all duration-200",
                  formData.priority === priority
                    ? priority === 'high'
                      ? 'border-red-500 bg-red-500/10 text-red-600 dark:text-red-500'
                      : priority === 'medium'
                      ? 'border-amber-500 bg-amber-500/10 text-amber-600 dark:text-amber-500'
                      : 'border-emerald-500 bg-emerald-500/10 text-emerald-600 dark:text-emerald-500'
                    : 'border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#141414] text-stone-500 dark:text-stone-400 hover:border-stone-300 dark:hover:border-stone-700 hover:text-stone-900 dark:hover:text-stone-300'
                )}
              >
                {priority}
              </button>
            ))}
          </div>
        </div>

        {/* Due Date */}
        <div className="space-y-2">
          <label htmlFor="due_date" className="block text-[10px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase tracking-[0.2em]">
            EXECUTION_DEADLINE
          </label>
          <input
            type="date"
            id="due_date"
            value={formData.due_date}
            onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
            className="w-full px-4 py-3 bg-stone-50 dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] text-stone-900 dark:text-white text-sm focus:outline-none focus:border-emerald-600/60 transition-colors"
          />
        </div>

        {/* Tags */}
        <div className="md:col-span-2 space-y-2">
          <label htmlFor="tag-input" className="block text-[10px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase tracking-[0.2em]">
            SYSTEM_LABELS
          </label>
          <div className="flex flex-wrap gap-2 mb-3">
            {formData.tags?.map((tag, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2 py-1 rounded-[2px] text-[10px] font-mono bg-stone-100 dark:bg-stone-900 border border-stone-200 dark:border-stone-800 text-stone-600 dark:text-stone-400"
              >
                #{tag}
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  aria-label={`Remove tag ${tag}`}
                  className="ml-1.5 p-1 -m-0.5 text-stone-500 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                >
                  <XMarkIcon className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              id="tag-input"
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Add identifier..."
              className="flex-1 px-4 py-2.5 bg-stone-50 dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] text-stone-900 dark:text-white text-sm focus:outline-none focus:border-emerald-600/60 transition-colors placeholder:text-stone-400 dark:placeholder:text-stone-600 placeholder:font-mono placeholder:text-[10px] placeholder:uppercase placeholder:tracking-widest"
            />
            <button
              type="button"
              onClick={addTag}
              className="px-4 py-2.5 min-h-10 bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-300 text-[10px] font-mono font-bold uppercase tracking-widest rounded-[4px] hover:bg-stone-200 dark:hover:bg-stone-700 transition-colors border border-stone-200 dark:border-stone-700"
            >
              Add
            </button>
          </div>
        </div>
      </div>

      {/* Action Matrix */}
      <div className="flex justify-end space-x-3 pt-6 border-t border-stone-100 dark:border-stone-900">
        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="px-6 min-h-11 bg-transparent text-[10px] font-mono font-bold text-stone-500 dark:text-stone-400 uppercase tracking-[0.2em] hover:text-stone-900 dark:hover:text-white transition-colors"
        >
          Abort
        </button>
        <button
          type="submit"
          disabled={isLoading || !formData.title.trim()}
          className="px-8 min-h-11 bg-emerald-600 text-white text-[10px] font-mono font-bold uppercase tracking-[0.2em] rounded-[4px] hover:bg-emerald-500 shadow-sm transition-all disabled:opacity-50"
        >
          {isLoading ? 'Processing...' : 'Initialize'}
        </button>
      </div>
    </motion.form>
  );
}