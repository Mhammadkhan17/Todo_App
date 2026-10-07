'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import ChatInterface from '@/components/rag/ChatInterface';
import DocumentsPanel, {
  IndexedDocument,
  UploadState,
} from '@/components/rag/DocumentsPanel';
import SessionSidebar, { RagSession } from '@/components/rag/SessionSidebar';
import LuxuryDashboardLayout from '@/components/layout/LuxuryDashboardLayout';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';
import { Terminal, X, FileText, History, Menu, Moon, Sun } from 'lucide-react';
import { toast } from 'sonner';

const SESSION_KEY = 'active_chat_session';
const ACCEPTED = ['pdf', 'txt', 'md', 'markdown', 'docx'];
const UPLOAD_IDLE: UploadState = {
  phase: 'idle',
  progress: 0,
  elapsed: 0,
  message: null,
  success: true,
  indexedCount: null,
};

export type UploadScope = 'universal' | 'chat';

export default function ChatPage() {
  const { isAuthenticated, loading, user, token, logout } = useAuth();
  const router = useRouter();
  const [docsOpen, setDocsOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sessions, setSessions] = useState<RagSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<IndexedDocument[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [upload, setUpload] = useState<UploadState>(UPLOAD_IDLE);
  const [uploadScope, setUploadScope] = useState<UploadScope>('universal');
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [drawersMounted, setDrawersMounted] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const [resolvedDark, setResolvedDark] = useState(false);

  // Same system-resolution trick the layout uses (avoids hydration mismatch)
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () =>
      setResolvedDark(
        theme === 'dark' || (theme === 'system' && media.matches)
      );
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [theme]);

  // Drawers render into document.body so the layout's `relative z-10`
  // stacking context can't trap them beneath the dashboard sidebar.
  useEffect(() => {
    setDrawersMounted(true);
  }, []);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, loading, router]);

  useEffect(() => {
    return () => {
      if (elapsedRef.current) clearInterval(elapsedRef.current);
    };
  }, []);

  const loadSessions = useCallback(
    async (restoreId: string | null) => {
      setSessionsLoading(true);
      try {
        const response = await fetch('/api/rag/sessions', {
          headers: { Authorization: `Bearer ${token || ''}` },
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const list: RagSession[] = data.sessions || [];
        setSessions(list);

        // Drop a restored session that no longer exists
        if (restoreId && !list.some(s => s.id === restoreId)) {
          setActiveSessionId(null);
          localStorage.removeItem(SESSION_KEY);
        }
      } catch (error) {
        console.error('Failed to load sessions:', error);
      } finally {
        setSessionsLoading(false);
      }
    },
    [token]
  );

  const loadDocuments = useCallback(async () => {
    setDocsLoading(true);
    setDocsError(false);
    try {
      const response = await fetch('/api/rag/documents', {
        headers: { Authorization: `Bearer ${token || ''}` },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocsError(true);
    } finally {
      setDocsLoading(false);
    }
  }, [token]);

  // Restore last active session, then load history + documents
  useEffect(() => {
    if (!isAuthenticated) return;
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored) setActiveSessionId(stored);
    loadSessions(stored);
    loadDocuments();
  }, [isAuthenticated, loadSessions, loadDocuments]);

  const selectSession = (id: string) => {
    setActiveSessionId(id);
    localStorage.setItem(SESSION_KEY, id);
    setHistoryOpen(false);
  };

  const newChat = () => {
    setActiveSessionId(null);
    localStorage.removeItem(SESSION_KEY);
    setHistoryOpen(false);
  };

  const handleSessionCreated = useCallback(
    (id: string) => {
      // Adopt the new session unless the user switched mid-flight (stale
      // closure over activeSessionId keeps their choice).
      if (!activeSessionId) {
        localStorage.setItem(SESSION_KEY, id);
        setActiveSessionId(id);
      }
      // Refresh the sidebar so the new conversation shows up
      loadSessions(localStorage.getItem(SESSION_KEY));
    },
    [loadSessions, activeSessionId]
  );

  // Native OS file picker lives in the composer; this performs the upload
  const startUpload = useCallback(
    (picked: File[]) => {
      if (picked.length === 0 || !isAuthenticated) return;

      const valid = picked.filter(file => {
        const ext = file.name.split('.').pop()?.toLowerCase();
        return ACCEPTED.includes(ext || '');
      });
      if (valid.length !== picked.length) {
        toast.warning(
          `${picked.length - valid.length} unsupported file(s) were rejected`
        );
      }
      if (valid.length === 0) return;

      setDocsOpen(true); // show pipeline + registry while it works
      setUpload({
        phase: 'uploading',
        progress: 0,
        elapsed: 0,
        message: null,
        success: true,
        indexedCount: null,
      });

      const formData = new FormData();
      valid.forEach(file => formData.append('files', file));
      formData.append('scope', uploadScope);
      if (uploadScope === 'chat' && activeSessionId) {
        formData.append('session_id', activeSessionId);
      }

      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/rag/upload-and-index');
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

      xhr.upload.onprogress = e => {
        if (!e.lengthComputable) return;
        const pct = Math.round((e.loaded / e.total) * 100);
        setUpload(prev =>
          prev.phase === 'uploading'
            ? { ...prev, progress: Math.min(pct, 99) }
            : prev
        );
        if (pct >= 100) {
          // Body fully sent — server is now extracting/embedding/indexing
          setUpload(prev => ({ ...prev, phase: 'indexing', elapsed: 0 }));
          if (elapsedRef.current) clearInterval(elapsedRef.current);
          elapsedRef.current = setInterval(() => {
            setUpload(prev =>
              prev.phase === 'indexing'
                ? { ...prev, elapsed: prev.elapsed + 1 }
                : prev
            );
          }, 1000);
        }
      };

      xhr.onload = () => {
        if (elapsedRef.current) {
          clearInterval(elapsedRef.current);
          elapsedRef.current = null;
        }
        let payload: {
          success?: boolean;
          message?: string;
          indexed_count?: number | null;
        } | null = null;
        try {
          payload = JSON.parse(xhr.responseText);
        } catch {
          payload = null;
        }

        if (xhr.status >= 200 && xhr.status < 300 && payload) {
          setUpload({
            phase: 'done',
            progress: 100,
            elapsed: 0,
            message: payload.message || null,
            success: payload.success === true,
            indexedCount: payload.indexed_count ?? null,
          });
          if (payload.success) {
            toast.success(`Indexed ${payload.indexed_count ?? 0} document(s)`);
          } else {
            toast.error(payload.message || 'Some files failed to index');
          }
          loadDocuments();
        } else {
          setUpload({
            phase: 'error',
            progress: 0,
            elapsed: 0,
            message: `Upload failed (HTTP ${xhr.status})`,
            success: false,
            indexedCount: null,
          });
          toast.error(`Upload failed (HTTP ${xhr.status})`);
        }
      };

      xhr.onerror = () => {
        if (elapsedRef.current) {
          clearInterval(elapsedRef.current);
          elapsedRef.current = null;
        }
        setUpload({
          phase: 'error',
          progress: 0,
          elapsed: 0,
          message: 'Network error — the upload was interrupted',
          success: false,
          indexedCount: null,
        });
        toast.error('Network error during upload');
      };

      xhr.send(formData);
    },
    [isAuthenticated, token, uploadScope, activeSessionId, loadDocuments]
  );

  const deleteDocument = useCallback(
    async (doc: IndexedDocument) => {
      setDeletingId(doc.id);
      try {
        const response = await fetch(
          `/api/rag/documents/${encodeURIComponent(doc.id)}`,
          {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token || ''}` },
          }
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setDocuments(prev => prev.filter(d => d.id !== doc.id));
        toast.success(`Removed ${doc.original_filename}`);
      } catch (error) {
        console.error('Delete failed:', error);
        toast.error(`Could not delete ${doc.original_filename}`);
      } finally {
        setDeletingId(null);
      }
    },
    [token]
  );

  const toggleKeep = useCallback(
    async (doc: IndexedDocument) => {
      setTogglingId(doc.id);
      try {
        const next = !doc.is_active;
        const response = await fetch(
          `/api/rag/documents/${encodeURIComponent(doc.id)}`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token || ''}`,
            },
            body: JSON.stringify({ is_active: next }),
          }
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        setDocuments(prev =>
          prev.map(d => (d.id === doc.id ? { ...d, is_active: next } : d))
        );
        toast.message(
          next
            ? `${doc.original_filename} will be used in answers`
            : `${doc.original_filename} kept but excluded from answers`
        );
      } catch (error) {
        console.error('Keep-toggle failed:', error);
        toast.error(`Could not update ${doc.original_filename}`);
      } finally {
        setTogglingId(null);
      }
    },
    [token]
  );

  // Chat-scoped uploads made before any session exists: derived from the
  // registry, sent with the next chat message, bound server-side there.
  const pendingDocumentIds = documents
    .filter(d => d.scope === 'chat' && d.session_id == null)
    .map(d => d.id);

  const activeTitle =
    sessions.find(s => s.id === activeSessionId)?.title || 'New_Conversation';

  // Show loading state while checking authentication
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  // Don't render if unauthenticated (will redirect via useEffect)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <LuxuryDashboardLayout user={user || null} onLogout={logout} immersive>
      <div className="flex h-[100dvh] min-h-96">
        {/* Chat fills the whole right column — no card frame, edge-to-edge */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          {/* Header: nav+history (left) · title (center) · theme+docs (right) */}
          <div className="h-14 shrink-0 flex items-center justify-between px-2 sm:px-3 border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#141414]">
            <div className="flex items-center">
              <button
                type="button"
                onClick={() => window.dispatchEvent(new Event('app:open-nav'))}
                aria-label="Open navigation"
                className="lg:hidden min-h-11 min-w-11 flex items-center justify-center rounded-[4px] text-stone-500 hover:text-stone-900 dark:hover:text-white hover:bg-stone-100 dark:hover:bg-[#1a1a1a] transition-colors"
              >
                <Menu className="h-4 w-4" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => setHistoryOpen(true)}
                aria-label="Show conversation history"
                aria-expanded={historyOpen}
                className="min-h-11 min-w-11 flex items-center justify-center rounded-[4px] text-stone-500 hover:text-stone-900 dark:hover:text-white hover:bg-stone-100 dark:hover:bg-[#1a1a1a] transition-colors"
              >
                <History className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <div className="flex items-center gap-2 sm:gap-3 min-w-0 px-2">
              <div className="w-6 h-6 bg-emerald-500 flex items-center justify-center rounded-[2px] shrink-0">
                <Terminal className="h-3.5 w-3.5 text-[#0a0a0a]" />
              </div>
              <div className="min-w-0 text-center">
                <h2 className="font-mono text-[11px] font-bold uppercase tracking-widest text-stone-900 dark:text-white truncate">
                  {'//'} Knowledge_Workspace
                </h2>
                <div className="flex items-center justify-center gap-1.5 mt-0.5 min-w-0">
                  <span
                    className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse shrink-0"
                    aria-hidden="true"
                  ></span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500 truncate">
                    {activeTitle}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center">
              <button
                type="button"
                onClick={toggleTheme}
                aria-label={
                  resolvedDark ? 'Switch to light theme' : 'Switch to dark theme'
                }
                className="min-h-11 min-w-11 flex items-center justify-center rounded-[4px] text-stone-500 hover:text-stone-900 dark:hover:text-white hover:bg-stone-100 dark:hover:bg-[#1a1a1a] transition-colors"
              >
                {resolvedDark ? (
                  <Sun className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Moon className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
              <button
                type="button"
                onClick={() => setDocsOpen(true)}
                aria-label="Show documents"
                aria-expanded={docsOpen}
                className="min-h-11 min-w-11 flex items-center justify-center rounded-[4px] text-stone-500 hover:text-stone-900 dark:hover:text-white hover:bg-stone-100 dark:hover:bg-[#1a1a1a] transition-colors"
              >
                <FileText className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>

          {/* Messages + Composer */}
          <ChatInterface
            sessionId={activeSessionId}
            onSessionCreated={handleSessionCreated}
            uploadScope={uploadScope}
            onToggleScope={() =>
              setUploadScope(prev => (prev === 'universal' ? 'chat' : 'universal'))
            }
            onFilesSelected={startUpload}
            pendingDocumentIds={pendingDocumentIds}
            onDocumentsBound={loadDocuments}
          />
        </div>
      </div>

      {drawersMounted &&
        createPortal(
          <>
            {/* Backdrop for either drawer */}
            {(historyOpen || docsOpen) && (
              <div
                className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm"
                onClick={() => {
                  setHistoryOpen(false);
                  setDocsOpen(false);
                }}
                aria-hidden="true"
              />
            )}

            {/* History drawer (hidden behind the clock icon) */}
            <aside
              aria-label="Conversation history"
              aria-hidden={!historyOpen}
              inert={!historyOpen}
              className={cn(
                'fixed inset-y-0 left-0 z-[100] w-80 max-w-[calc(100vw-2rem)] bg-white dark:bg-[#0f0f0f] border-r border-stone-200 dark:border-stone-800 overflow-hidden shadow-xl transition-transform duration-200',
                historyOpen ? 'translate-x-0' : '-translate-x-full'
              )}
            >
              <div className="flex items-center justify-between px-4 h-14 shrink-0 border-b border-stone-200 dark:border-stone-800">
                <span className="font-mono text-[11px] font-bold uppercase tracking-widest text-stone-900 dark:text-white">
                  History
                </span>
                <button
                  type="button"
                  onClick={() => setHistoryOpen(false)}
                  aria-label="Close history panel"
                  className="min-h-11 min-w-11 -mr-3 flex items-center justify-center text-stone-500 hover:text-stone-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              <div className="flex-1 min-h-0 h-[calc(100%-3.5rem)]">
                <SessionSidebar
                  sessions={sessions}
                  activeId={activeSessionId}
                  loading={sessionsLoading}
                  onSelect={selectSession}
                  onNew={newChat}
                />
              </div>
            </aside>

            {/* Documents drawer (behind the file icon) */}
            <aside
              aria-label="Documents"
              aria-hidden={!docsOpen}
              inert={!docsOpen}
              className={cn(
                'fixed inset-y-0 right-0 z-[100] w-80 max-w-[calc(100vw-2rem)] bg-white dark:bg-[#0f0f0f] border-l border-stone-200 dark:border-stone-800 overflow-hidden shadow-xl transition-transform duration-200',
                docsOpen ? 'translate-x-0' : 'translate-x-full'
              )}
            >
              <div className="flex items-center justify-between px-4 h-14 shrink-0 border-b border-stone-200 dark:border-stone-800">
                <span className="font-mono text-[11px] font-bold uppercase tracking-widest text-stone-900 dark:text-white">
                  Documents
                </span>
                <button
                  type="button"
                  onClick={() => setDocsOpen(false)}
                  aria-label="Close documents panel"
                  className="min-h-11 min-w-11 -mr-3 flex items-center justify-center text-stone-500 hover:text-stone-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              <div className="flex-1 min-h-0 h-[calc(100%-3.5rem)] p-4">
                <DocumentsPanel
                  documents={documents}
                  loading={docsLoading}
                  error={docsError}
                  onRetry={loadDocuments}
                  upload={upload}
                  deletingId={deletingId}
                  togglingId={togglingId}
                  onDelete={deleteDocument}
                  onToggleKeep={toggleKeep}
                />
              </div>
            </aside>
          </>,
          document.body
        )}
    </LuxuryDashboardLayout>
  );
}
