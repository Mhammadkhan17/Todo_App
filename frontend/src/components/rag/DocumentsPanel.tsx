'use client';

import React from 'react';
import {
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2,
  Trash2,
  Database,
} from 'lucide-react';
import { cn, formatTaskTimeAgo } from '@/lib/utils';

export interface IndexedDocument {
  id: string;
  original_filename: string;
  file_size: number | null;
  status: string;
  scope: string;
  session_id: string | null;
  is_active: boolean;
  created_at?: string;
}

export type UploadPhase = 'idle' | 'uploading' | 'indexing' | 'done' | 'error';

export interface UploadState {
  phase: UploadPhase;
  progress: number;
  elapsed: number;
  message: string | null;
  success: boolean;
  indexedCount: number | null;
}

interface DocumentsPanelProps {
  documents: IndexedDocument[];
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  upload: UploadState;
  deletingId: string | null;
  togglingId: string | null;
  onDelete: (doc: IndexedDocument) => void;
  onToggleKeep: (doc: IndexedDocument) => void;
}

const formatSize = (bytes: number | null): string => {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
};

const statusStyles: Record<string, string> = {
  indexed: 'border-emerald-600/40 text-emerald-700 dark:text-emerald-400 bg-emerald-500/10',
  processing: 'border-amber-600/40 text-amber-700 dark:text-amber-400 bg-amber-500/10',
  failed: 'border-red-600/40 text-red-700 dark:text-red-400 bg-red-500/10',
};

const scopeStyles: Record<string, string> = {
  universal: 'border-sky-600/40 text-sky-700 dark:text-sky-400 bg-sky-500/10',
  chat: 'border-violet-600/40 text-violet-700 dark:text-violet-400 bg-violet-500/10',
};

const scopeLabels: Record<string, string> = {
  universal: 'All_Chats',
  chat: 'This_Chat',
};

const DocumentsPanel = ({
  documents,
  loading,
  error,
  onRetry,
  upload,
  deletingId,
  togglingId,
  onDelete,
  onToggleKeep,
}: DocumentsPanelProps) => {
  return (
    <div className="flex flex-col gap-4 h-full min-h-0 overflow-y-auto custom-scrollbar">
      {/* Upload pipeline (fed by the composer's native picker) */}
      {upload.phase !== 'idle' && (
        <section className="border border-stone-200 dark:border-stone-800 rounded-[4px] p-3 bg-white dark:bg-[#141414]">
          <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-stone-500 dark:text-stone-400 mb-2">
            {'//'} Upload_Pipeline
          </p>

          {upload.phase === 'uploading' && (
            <>
              <div className="flex items-center justify-between mb-2">
                <span className="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-widest text-stone-600 dark:text-stone-400">
                  <Loader2 className="h-3 w-3 animate-spin text-emerald-600" aria-hidden="true" />
                  Uploading
                </span>
                <span className="font-mono text-[10px] text-stone-500">
                  {upload.progress}%
                </span>
              </div>
              <div className="h-1 w-full bg-stone-200 dark:bg-stone-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-150"
                  style={{ width: `${upload.progress}%` }}
                />
              </div>
            </>
          )}

          {upload.phase === 'indexing' && (
            <div className="flex items-center gap-2">
              <Loader2
                className="h-3.5 w-3.5 animate-spin text-emerald-600 dark:text-emerald-400"
                aria-hidden="true"
              />
              <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-stone-600 dark:text-stone-400">
                Extracting + chunking + embedding
              </span>
              <span className="ml-auto font-mono text-[10px] text-stone-500 dark:text-stone-500">
                {upload.elapsed}s
              </span>
            </div>
          )}

          {(upload.phase === 'done' || upload.phase === 'error') && upload.message && (
            <div className="flex items-start gap-2">
              {upload.success ? (
                <CheckCircle
                  className="h-3.5 w-3.5 mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400"
                  aria-hidden="true"
                />
              ) : (
                <AlertCircle
                  className="h-3.5 w-3.5 mt-0.5 shrink-0 text-red-600"
                  aria-hidden="true"
                />
              )}
              <div className="min-w-0">
                <p
                  className={cn(
                    'font-mono text-[10px] font-bold uppercase tracking-widest',
                    upload.success
                      ? 'text-emerald-700 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  )}
                >
                  {upload.phase === 'error'
                    ? 'Upload_failed'
                    : upload.success
                      ? `Done — ${upload.indexedCount ?? 0} indexed`
                      : 'Completed with errors'}
                </p>
                <p className="mt-1 text-xs text-stone-600 dark:text-stone-400 break-words">
                  {upload.message}
                </p>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Registry */}
      <section className="flex flex-col min-h-0 flex-1">
        <div className="flex items-center justify-between mb-3">
          <p className="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-widest text-stone-500 dark:text-stone-400">
            <Database className="h-3 w-3" aria-hidden="true" />
            Document_Registry
          </p>
          <span className="font-mono text-[10px] text-stone-500 dark:text-stone-500">
            {documents.length}
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2
              className="h-4 w-4 text-emerald-600 dark:text-emerald-400 animate-spin"
              aria-hidden="true"
            />
          </div>
        ) : error ? (
          <div className="py-4 text-center">
            <p className="font-mono text-[10px] uppercase tracking-widest text-red-600 dark:text-red-400">
              Failed to load registry
            </p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 px-3 py-1.5 border border-stone-300 dark:border-stone-700 rounded-[4px] font-mono text-[10px] font-bold uppercase tracking-widest text-stone-600 dark:text-stone-300 hover:border-emerald-600/40 hover:text-stone-900 dark:hover:text-white transition-colors"
            >
              Retry
            </button>
          </div>
        ) : documents.length === 0 ? (
          <p className="py-4 text-center font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
            No documents yet — attach one with the paperclip
          </p>
        ) : (
          <ul className="space-y-1.5">
            {documents.map(doc => (
              <li
                key={doc.id}
                className="flex items-center gap-2 px-2.5 py-2 border border-stone-200 dark:border-stone-800 rounded-[4px] bg-white dark:bg-[#141414]"
              >
                <FileText
                  className={cn(
                    'h-3.5 w-3.5 shrink-0',
                    doc.is_active
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-stone-300 dark:text-stone-600'
                  )}
                  aria-hidden="true"
                />
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      'text-xs truncate',
                      doc.is_active
                        ? 'text-stone-800 dark:text-stone-200'
                        : 'text-stone-400 dark:text-stone-600 line-through decoration-stone-300 dark:decoration-stone-700'
                    )}
                  >
                    {doc.original_filename}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-1">
                    <span
                      className={cn(
                        'shrink-0 border rounded-[2px] px-1.5 py-0.5 font-mono text-[8px] font-bold uppercase tracking-widest',
                        statusStyles[doc.status] || statusStyles.processing
                      )}
                    >
                      {doc.status}
                    </span>
                    <span
                      className={cn(
                        'shrink-0 border rounded-[2px] px-1.5 py-0.5 font-mono text-[8px] font-bold uppercase tracking-widest',
                        scopeStyles[doc.scope] || scopeStyles.universal
                      )}
                    >
                      {scopeLabels[doc.scope] || 'All_Chats'}
                    </span>
                    <span className="font-mono text-[9px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
                      {formatSize(doc.file_size)}
                      {doc.created_at ? ` · ${formatTaskTimeAgo(doc.created_at)}` : ''}
                    </span>
                  </div>
                </div>

                {/* Keep-toggle: off = kept in library, excluded from retrieval */}
                <button
                  type="button"
                  role="switch"
                  aria-checked={doc.is_active}
                  aria-label={`Keep ${doc.original_filename} in retrieval`}
                  onClick={() => onToggleKeep(doc)}
                  disabled={togglingId === doc.id}
                  className="shrink-0 min-h-8 min-w-8 flex items-center justify-center disabled:opacity-40"
                >
                  <span
                    className={cn(
                      'relative w-7 h-4 rounded-full transition-colors inline-block',
                      doc.is_active
                        ? 'bg-emerald-600'
                        : 'bg-stone-300 dark:bg-stone-700'
                    )}
                  >
                    <span
                      className={cn(
                        'absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white transition-transform',
                        doc.is_active && 'translate-x-3'
                      )}
                    />
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => onDelete(doc)}
                  disabled={deletingId === doc.id}
                  aria-label={`Delete ${doc.original_filename}`}
                  className="min-h-8 min-w-8 flex items-center justify-center text-stone-400 hover:text-red-600 dark:hover:text-red-400 disabled:opacity-40"
                >
                  {deletingId === doc.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};

export default DocumentsPanel;
