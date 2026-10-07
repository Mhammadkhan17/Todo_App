'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Send, Bot, FileText, Loader2, Square, Copy, Check, RotateCcw, X, Paperclip, Globe, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sources?: Array<{
    content: string;
    metadata: Record<string, unknown>;
  }>;
}

interface ChatInterfaceProps {
  sessionId: string | null;
  onSessionCreated: (sessionId: string) => void;
  uploadScope: 'universal' | 'chat';
  onToggleScope: () => void;
  onFilesSelected: (files: File[]) => void;
  pendingDocumentIds: string[];
  onDocumentsBound: () => void;
}

const EXAMPLE_PROMPTS = [
  'Summarize my uploaded documents',
  'What are the key dates mentioned in my notes?',
  'List the action items across my documents',
];

const ChatInterface = ({
  sessionId,
  onSessionCreated,
  uploadScope,
  onToggleScope,
  onFilesSelected,
  pendingDocumentIds,
  onDocumentsBound,
}: ChatInterfaceProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Stick-to-bottom: only follow new messages while the reader is already near
  // the bottom; release as soon as they scroll up (150px threshold).
  const stickToBottomRef = useRef(true);
  const { user, token, isAuthenticated } = useAuth();

  const handleScroll = () => {
    const el = scrollAreaRef.current;
    if (!el) return;
    stickToBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < 150;
  };

  // Auto-scroll to bottom when messages change (only if still sticking)
  useEffect(() => {
    if (scrollAreaRef.current && stickToBottomRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  // Auto-grow textarea, capped at ~6 lines
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [inputValue]);

  // Load conversation history when the active session changes
  useEffect(() => {
    let cancelled = false;
    stickToBottomRef.current = true;

    if (!sessionId || !isAuthenticated) {
      setMessages([]);
      return;
    }

    const load = async () => {
      setIsLoadingHistory(true);
      try {
        const response = await fetch(
          `/api/rag/sessions/${sessionId}/messages`,
          {
            headers: { Authorization: `Bearer ${token || ''}` },
          }
        );
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (cancelled) return;
        const loaded: Message[] = (data.messages || []).map(
          (m: {
            id?: string;
            role: string;
            content: string;
            sources?: Message['sources'];
            created_at?: string;
          }) => ({
            id: m.id || `${m.role}-${m.created_at}`,
            content: m.content,
            role: m.role === 'user' ? 'user' : 'assistant',
            timestamp: m.created_at ? new Date(m.created_at) : new Date(),
            sources: m.sources || [],
          })
        );
        setMessages(loaded);
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load conversation:', error);
          toast.error('Could not load this conversation');
        }
      } finally {
        if (!cancelled) setIsLoadingHistory(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId, isAuthenticated, token]);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();

      if (!inputValue.trim() || isLoading || !isAuthenticated) return;

      const userMessage: Message = {
        id: Date.now().toString(),
        content: inputValue,
        role: 'user',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, userMessage]);
      setInputValue('');
      setSendError(null);
      setIsLoading(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch('/api/rag/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token || ''}`,
          },
          body: JSON.stringify({
            message: userMessage.content,
            session_id: sessionId || undefined,
            user_id: user?.id?.toString(),
            // Chat-scoped uploads made before a session existed: bind them
            // to this conversation server-side with this first message.
            document_ids: pendingDocumentIds.length
              ? pendingDocumentIds
              : undefined,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.session_id && !sessionId) {
          onSessionCreated(data.session_id);
        }

        if (pendingDocumentIds.length > 0) {
          onDocumentsBound();
        }

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.response,
          role: 'assistant',
          timestamp: new Date(),
          sources: data.sources || [],
        };

        setMessages(prev => [...prev, assistantMessage]);
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          // User pressed Stop: keep the question, drop the pending answer.
          toast.message('Generation stopped');
        } else {
          console.error('Error sending message:', error);
          toast.error('Request failed — check your connection and try again');
          // Roll back the optimistic user message so the retry is clean
          setMessages(prev => prev.filter(m => m.id !== userMessage.id));
          setInputValue(userMessage.content);
          setSendError(userMessage.content);
        }
      } finally {
        abortRef.current = null;
        setIsLoading(false);
      }
    },
    [inputValue, isLoading, isAuthenticated, token, user, sessionId, onSessionCreated, pendingDocumentIds, onDocumentsBound]
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const handleCopy = useCallback(async (message: Message) => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedId(message.id);
      setTimeout(() => setCopiedId(null), 1500);
    } catch {
      toast.error('Could not copy to clipboard');
    }
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      // Don't submit while an IME composition (CJK input) is in progress
      if (e.nativeEvent.isComposing) return;
      e.preventDefault();
      handleSubmit();
    }
  };

  const formatSourceMetadata = (metadata: Record<string, unknown>) => {
    const { source, file_name, ...other } = metadata;
    const fileName = typeof file_name === 'string' ? file_name : undefined;
    const sourceName = typeof source === 'string' ? source : undefined;
    return (
      <div className="text-[10px] font-mono uppercase tracking-wider text-stone-500 dark:text-stone-500">
        {fileName && (
          <span className="font-bold text-stone-700 dark:text-stone-300">
            {fileName}
          </span>
        )}
        {sourceName && !fileName && <span>{sourceName}</span>}
        {Object.keys(other).length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {Object.entries(other).map(([key, value]) => (
              <span
                key={key}
                className="bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-[2px] px-1.5 py-0.5"
              >
                {key}: {String(value)}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Message Log */}
      <div
        ref={scrollAreaRef}
        onScroll={handleScroll}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Chat messages"
        className="flex-1 overflow-y-auto px-4 py-6 bg-stone-50/50 dark:bg-[#0a0a0a] custom-scrollbar scroll-smooth"
      >
        {isLoadingHistory ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Loader2
              className="h-5 w-5 text-emerald-600 dark:text-emerald-400 animate-spin"
              aria-hidden="true"
            />
            <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
              Loading_conversation...
            </p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-12 h-12 mb-4 bg-emerald-500/10 border border-emerald-500/20 rounded-[4px] flex items-center justify-center">
              <Bot className="h-6 w-6 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
            </div>
            <p className="font-mono text-[11px] font-bold uppercase tracking-widest text-stone-900 dark:text-white">
              Awaiting_Input
            </p>
            <p className="mt-2 font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
              Ask about your uploaded documents
            </p>
            <div className="mt-6 flex flex-col gap-2 w-full max-w-md">
              {EXAMPLE_PROMPTS.map(prompt => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setInputValue(prompt)}
                  disabled={isLoading}
                  className="text-left text-xs px-3 py-2.5 border border-stone-200 dark:border-stone-800 rounded-[4px] bg-white dark:bg-[#141414] text-stone-600 dark:text-stone-400 hover:border-emerald-600/40 hover:text-stone-900 dark:hover:text-white transition-colors disabled:opacity-60"
                >
                  <span className="text-emerald-600 dark:text-emerald-400 font-mono mr-2">
                    {'>'}
                  </span>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6 max-w-3xl mx-auto w-full">
            {messages.map(message => (
              <div
                key={message.id}
                className={cn(
                  'flex flex-col gap-2',
                  message.role === 'user' ? 'items-end' : 'items-start'
                )}
              >
                {/* Role label + timestamp */}
                <div className="flex items-center gap-2 px-1">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-stone-600 dark:text-stone-400">
                    {message.role === 'user' ? 'Identity_User' : 'Core_Assistant'}
                  </span>
                  <span className="font-mono text-[10px] text-stone-500 dark:text-stone-500">
                    {message.timestamp.toLocaleTimeString([], {
                      hour12: false,
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </span>
                  {message.role === 'assistant' && (
                    <button
                      type="button"
                      onClick={() => handleCopy(message)}
                      aria-label={
                        copiedId === message.id
                          ? 'Answer copied'
                          : 'Copy answer'
                      }
                      className="text-stone-400 dark:text-stone-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                    >
                      {copiedId === message.id ? (
                        <Check className="h-3 w-3" aria-hidden="true" />
                      ) : (
                        <Copy className="h-3 w-3" aria-hidden="true" />
                      )}
                    </button>
                  )}
                </div>

                {/* Bubble */}
                <div
                  className={cn(
                    'rounded-[4px] px-4 py-3 max-w-[85%] border',
                    message.role === 'user'
                      ? 'bg-emerald-50 dark:bg-emerald-500/10 border-stone-200 dark:border-stone-800 border-l-2 border-l-emerald-600 text-stone-900 dark:text-stone-100'
                      : 'bg-white dark:bg-[#141414] border-stone-200 dark:border-stone-800 text-stone-800 dark:text-stone-200'
                  )}
                >
                  {message.role === 'user' ? (
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {message.content}
                    </p>
                  ) : (
                    <div className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}

                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-stone-200 dark:border-stone-800">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText
                          className="h-3 w-3 text-emerald-600 dark:text-emerald-400"
                          aria-hidden="true"
                        />
                        <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-400">
                          Sources [{message.sources.length}]
                        </span>
                      </div>
                      <div className="space-y-2">
                        {message.sources.slice(0, 3).map((source, idx) => (
                          <div
                            key={idx}
                            className="text-xs bg-stone-50 dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] p-2.5"
                          >
                            <div className="line-clamp-2 text-stone-600 dark:text-stone-400">
                              {source.content}
                            </div>
                            <div className="mt-1.5">
                              {formatSourceMetadata(source.metadata)}
                            </div>
                          </div>
                        ))}
                        {message.sources.length > 3 && (
                          <p className="font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
                            +{message.sources.length - 3} more sources
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex flex-col gap-2 items-start">
                <span className="px-1 font-mono text-[10px] font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-400">
                  Processing
                </span>
                <div className="bg-white dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] px-4 py-3 flex items-center gap-3">
                  <Loader2
                    className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-500 animate-spin"
                    aria-hidden="true"
                  />
                  <span className="font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
                    Retrieving_context + generating_answer...
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Send failure: offer an explicit retry (input is already restored) */}
      {sendError !== null && (
        <div
          role="alert"
          className="shrink-0 border-t border-red-300/60 dark:border-red-900/60 bg-red-50 dark:bg-red-950/30 px-4 py-2"
        >
          <div className="flex items-center justify-between gap-3 max-w-3xl mx-auto w-full">
            <p className="font-mono text-[10px] uppercase tracking-widest text-red-700 dark:text-red-400">
              Request_failed — message rolled back
            </p>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isLoading || !inputValue.trim()}
                className="flex items-center gap-1.5 px-2.5 py-1.5 border border-red-300 dark:border-red-900 rounded-[4px] font-mono text-[10px] font-bold uppercase tracking-widest text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors disabled:opacity-60"
              >
                <RotateCcw className="h-3 w-3" aria-hidden="true" />
                Retry
              </button>
              <button
                type="button"
                onClick={() => setSendError(null)}
                aria-label="Dismiss error"
                className="p-1.5 text-red-400 dark:text-red-500 hover:text-red-700 dark:hover:text-red-400 transition-colors"
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Composer */}
      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-stone-200 dark:border-stone-800 bg-white dark:bg-[#0f0f0f] p-4"
      >
        <div className="flex flex-col gap-2 max-w-3xl mx-auto w-full">
          {/* Upload scope + pending bindings */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onToggleScope}
              aria-pressed={uploadScope === 'chat'}
              aria-label={`Upload scope: ${
                uploadScope === 'universal' ? 'All chats' : 'This chat'
              }. Toggle.`}
              className={cn(
                'flex items-center gap-1.5 px-2 py-1 border rounded-[4px] font-mono text-[10px] font-bold uppercase tracking-widest transition-colors',
                uploadScope === 'universal'
                  ? 'border-sky-600/40 text-sky-700 dark:text-sky-400 bg-sky-500/10'
                  : 'border-violet-600/40 text-violet-700 dark:text-violet-400 bg-violet-500/10'
              )}
            >
              {uploadScope === 'universal' ? (
                <Globe className="h-3 w-3" aria-hidden="true" />
              ) : (
                <MessageSquare className="h-3 w-3" aria-hidden="true" />
              )}
              {uploadScope === 'universal' ? 'All_Chats' : 'This_Chat'}
            </button>
            {pendingDocumentIds.length > 0 && (
              <span className="px-2 py-1 border border-emerald-600/40 text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 rounded-[4px] font-mono text-[10px] font-bold uppercase tracking-widest">
                {pendingDocumentIds.length} pending_bind
              </span>
            )}
          </div>

          <div className="flex gap-3 items-end">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Attach documents"
              disabled={isLoading}
              className="min-h-11 min-w-11 flex items-center justify-center border border-stone-200 dark:border-stone-800 rounded-[4px] text-stone-500 hover:text-stone-900 dark:hover:text-white hover:border-emerald-600/40 transition-colors disabled:opacity-60"
            >
              <Paperclip className="h-4 w-4" aria-hidden="true" />
            </button>
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Enter_Query_Payload... (Enter to send, Shift+Enter for newline)"
              aria-label="Ask a question about your documents"
              disabled={isLoading}
              className="flex-1 min-h-11 max-h-40 resize-none bg-stone-100 dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] px-4 py-3 text-sm text-stone-900 dark:text-white focus:outline-none focus:border-emerald-600/60 transition-colors placeholder:font-mono placeholder:text-[10px] placeholder:uppercase placeholder:tracking-widest placeholder:text-stone-500 dark:placeholder:text-stone-500 disabled:opacity-60 custom-scrollbar"
            />
            {isLoading ? (
              <button
                type="button"
                onClick={handleStop}
                aria-label="Stop generating"
                className="min-h-11 min-w-11 px-4 bg-stone-200 hover:bg-stone-300 dark:bg-stone-800 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-300 rounded-[4px] transition-all active:scale-95 flex items-center justify-center"
              >
                <Square className="h-3.5 w-3.5 fill-current" aria-hidden="true" />
              </button>
            ) : (
              <button
                type="submit"
                aria-label="Send message"
                disabled={!inputValue.trim() || !isAuthenticated}
                className="min-h-11 min-w-11 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-stone-200 disabled:text-stone-400 dark:disabled:bg-stone-900 dark:disabled:text-stone-700 text-[#0a0a0a] rounded-[4px] transition-all active:scale-95 flex items-center justify-center"
              >
                <Send className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>
        </div>

        {/* Native OS file picker */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.markdown,.docx"
          className="hidden"
          onChange={e => {
            const picked = Array.from(e.target.files || []);
            if (picked.length > 0) onFilesSelected(picked);
            e.target.value = ''; // allow re-picking the same file
          }}
        />
      </form>
    </>
  );
};

export default ChatInterface;
