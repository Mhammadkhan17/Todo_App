'use client';

import React, { useEffect, useState } from 'react';
import ChatInterface from '@/components/rag/ChatInterface';
import DocumentUploader from '@/components/rag/DocumentUploader';
import LuxuryDashboardLayout from '@/components/layout/LuxuryDashboardLayout';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Terminal, X, FileText, Database, MessageSquare } from 'lucide-react';

export default function ChatPage() {
  const { isAuthenticated, loading, user, logout } = useAuth();
  const router = useRouter();
  const [docsOpen, setDocsOpen] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, loading, router]);

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
    <LuxuryDashboardLayout user={user || null} onLogout={logout}>
      <div className="flex h-[calc(100dvh-11rem)] min-h-96 gap-6 lg:h-[calc(100dvh-13rem)]">
        {/* Chat Shell */}
        <div className="flex flex-col flex-1 min-w-0 bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] overflow-hidden">
          {/* Terminal Header */}
          <div className="h-14 shrink-0 flex items-center justify-between px-4 border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#141414]">
            <div className="flex items-center gap-3">
              <div className="w-6 h-6 bg-emerald-500 flex items-center justify-center rounded-[2px]">
                <Terminal className="h-3.5 w-3.5 text-[#0a0a0a]" />
              </div>
              <div>
                <h2 className="font-mono text-[11px] font-bold uppercase tracking-widest text-stone-900 dark:text-white">
                  {'//'} Knowledge_Assistant
                </h2>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse" aria-hidden="true"></span>
                  <span className="font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
                    Link_Active
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setDocsOpen(!docsOpen)}
              aria-expanded={docsOpen}
              aria-label={docsOpen ? 'Hide documents panel' : 'Show documents panel'}
              className={`min-h-11 px-3 flex items-center gap-2 rounded-[4px] border font-mono text-[10px] font-bold uppercase tracking-widest transition-colors ${
                docsOpen
                  ? 'border-emerald-600/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                  : 'border-stone-200 dark:border-stone-800 text-stone-500 dark:text-stone-400 hover:text-stone-900 dark:hover:text-white'
              }`}
            >
              <FileText className="h-3.5 w-3.5" aria-hidden="true" />
              Docs
            </button>
          </div>

          {/* Messages + Composer */}
          <ChatInterface />
        </div>

        {/* Documents Panel */}
        {docsOpen && (
          <>
            {/* Mobile backdrop */}
            <div
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
              onClick={() => setDocsOpen(false)}
              aria-hidden="true"
            />
            <aside
              aria-label="Documents"
              className="fixed inset-y-0 right-0 z-50 w-80 max-w-[calc(100vw-2rem)] bg-white dark:bg-[#0f0f0f] border-l border-stone-200 dark:border-stone-800 overflow-y-auto p-4 lg:static lg:z-auto lg:w-[340px] lg:shrink-0 lg:border-l lg:rounded-[4px]"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Database className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                  <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-stone-500 dark:text-stone-400">
                    Document_Registry
                  </span>
                </div>
                <button
                  onClick={() => setDocsOpen(false)}
                  aria-label="Close documents panel"
                  className="min-h-11 min-w-11 -mr-3 flex items-center justify-center text-stone-500 hover:text-stone-900 dark:hover:text-white"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>

              <DocumentUploader />

              <div className="mt-6 border-t border-stone-200 dark:border-stone-800 pt-4">
                <p className="font-mono text-[10px] font-bold uppercase tracking-widest text-stone-500 dark:text-stone-400 mb-3">
                  Protocol_How_It_Works
                </p>
                <ul className="space-y-2.5 text-xs text-stone-600 dark:text-stone-400">
                  <li className="flex items-start gap-2.5">
                    <MessageSquare className="h-3.5 w-3.5 mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                    <span>Upload documents in PDF, TXT, Markdown, or Word formats</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <Database className="h-3.5 w-3.5 mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                    <span>Documents are indexed with vector embeddings for retrieval</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <Terminal className="h-3.5 w-3.5 mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                    <span>Ask questions and get answers with cited sources</span>
                  </li>
                </ul>
              </div>
            </aside>
          </>
        )}
      </div>
    </LuxuryDashboardLayout>
  );
}
