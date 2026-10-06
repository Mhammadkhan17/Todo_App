'use client';

import React, { useState, useRef, useEffect, useSyncExternalStore } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Send, Bot, Minus, Maximize, Loader2, Terminal, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Persisted visibility store: the widget remounts on every route change,
// so open/closed lives in localStorage (default: open) instead of component state.
const VISIBILITY_KEY = 'chat_widget_visible';
const visibilityListeners = new Set<() => void>();

function notifyVisibility(): void {
  visibilityListeners.forEach((listener) => listener());
}

function subscribeVisibility(onStoreChange: () => void): () => void {
  visibilityListeners.add(onStoreChange);
  const onStorage = (event: StorageEvent) => {
    if (event.key === VISIBILITY_KEY || event.key === null) {
      onStoreChange();
    }
  };
  window.addEventListener('storage', onStorage);
  return () => {
    visibilityListeners.delete(onStoreChange);
    window.removeEventListener('storage', onStorage);
  };
}

function readVisibility(): boolean {
  try {
    return localStorage.getItem(VISIBILITY_KEY) !== 'false';
  } catch {
    return true;
  }
}

function getServerVisibility(): boolean {
  return true;
}

function writeVisibility(visible: boolean): void {
  try {
    localStorage.setItem(VISIBILITY_KEY, String(visible));
  } catch (e) {
    console.error('Failed to save chat widget visibility:', e);
  }
  notifyVisibility();
}

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

interface ChatWidgetProps {
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  onTaskUpdate?: () => void;
}

const CompactChatWidget: React.FC<ChatWidgetProps> = ({
  isExpanded: expandedProp = false,
  onToggleExpand,
  onTaskUpdate
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      content: 'System initialized. I am your **TodoFlow Assistant**. Ready to manage your task registry.',
      role: 'assistant',
      timestamp: new Date(),
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const isVisible = useSyncExternalStore(subscribeVisibility, readVisibility, getServerVisibility);
  const [isExpandedState, setIsExpandedState] = useState(expandedProp);

  const isExpanded = onToggleExpand ? expandedProp : isExpandedState;
  const toggleExpand = onToggleExpand || (() => setIsExpandedState(!isExpandedState));
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { user, isAuthenticated } = useAuth();

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading || !isAuthenticated || !user) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const { apiClient } = await import('@/lib/api');
      const response = await apiClient.client.post('/chat', {
        message: inputValue,
      });

      const data = response.data;
      
      if (data.tool_calls && data.tool_calls.length > 0 && onTaskUpdate) {
        onTaskUpdate();
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        role: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: '**CRITICAL_ERROR**: Operation failed. Connection to AI core interrupted.',
        role: 'assistant',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isVisible) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={() => writeVisibility(true)}
          aria-label="Open chat assistant"
          className="bg-emerald-600 hover:bg-emerald-500 text-[#0a0a0a] rounded-[4px] min-h-11 min-w-11 p-3 shadow-[0_0_30px_rgba(16,185,129,0.3)] transition-all active:scale-95 group"
        >
          <Bot className="h-6 w-6 group-hover:animate-pulse" />
        </button>
      </div>
    );
  }

  return (
    <div className={cn(
      "fixed bottom-6 right-6 z-50 transition-all duration-300 ease-[0.25,1,0.5,1] max-w-[calc(100vw-3rem)]",
      isExpanded ? 'w-[450px]' : 'w-80'
    )}>
      <div className="bg-white dark:bg-[#0f0f0f] border border-stone-200 dark:border-stone-800 rounded-[4px] shadow-[0_20px_50px_rgba(0,0,0,0.12)] dark:shadow-[0_20px_60px_rgba(0,0,0,0.6)] overflow-hidden">
        {/* Chat Header */}
        <div className="p-4 border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#141414] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-emerald-500 flex items-center justify-center rounded-[2px]">
              <Terminal className="h-3.5 w-3.5 text-[#0a0a0a]" />
            </div>
            <div>
              <h3 className="text-[12px] font-mono font-bold text-stone-900 dark:text-white uppercase tracking-widest">Assistant_Interface</h3>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse"></span>
                <span className="text-[10px] font-mono text-stone-500 dark:text-stone-500 uppercase">Secure_Session_Active</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={toggleExpand}
              aria-label={isExpanded ? 'Minimize chat' : 'Expand chat'}
              aria-expanded={isExpanded}
              className="min-h-11 min-w-11 flex items-center justify-center text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-white transition-colors"
            >
              {isExpanded ? <Minus className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
            </button>
            <button
              onClick={() => writeVisibility(false)}
              aria-label="Close chat"
              className="min-h-11 min-w-11 flex items-center justify-center text-stone-500 hover:text-red-600 dark:text-stone-400 dark:hover:text-red-400 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="p-4 bg-stone-50 dark:bg-[#0a0a0a]">
          <div
            ref={scrollAreaRef}
            role="log"
            aria-live="polite"
            aria-relevant="additions"
            aria-label="Chat messages"
            className="h-[350px] overflow-y-auto space-y-6 pr-2 custom-scrollbar scroll-smooth"
          >
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'flex flex-col gap-2',
                  message.role === 'user' ? 'items-end' : 'items-start'
                )}
              >
                <div className="flex items-center gap-2 px-1">
                  <span className="text-[10px] font-mono text-stone-600 dark:text-stone-500 uppercase tracking-widest font-bold">
                    {message.role === 'user' ? 'IDENTITY_USER' : 'CORE_ASSISTANT'}
                  </span>
                  <span className="text-[10px] font-mono text-stone-500 dark:text-stone-600">
                    {message.timestamp.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
                <div
                  className={cn(
                    'rounded-[4px] px-4 py-3 text-sm leading-relaxed border',
                    message.role === 'user'
                      ? 'bg-stone-100 border-stone-200 text-stone-900 dark:bg-stone-900 dark:border-stone-800 dark:text-stone-200'
                      : 'bg-white border-stone-200 text-stone-800 dark:bg-[#141414] dark:border-stone-800 dark:text-white dark:shadow-[0_4px_20px_rgba(0,0,0,0.2)]'
                  )}
                >
                  <div className="markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex flex-col gap-2 items-start animate-pulse">
                <div className="flex items-center gap-2 px-1">
                  <span className="text-[9px] font-mono text-emerald-700 dark:text-emerald-500 uppercase tracking-widest font-bold">CORE_PROCESSING</span>
                </div>
                <div className="bg-white border border-stone-200 dark:bg-[#141414] dark:border-stone-800 rounded-[4px] px-4 py-3 flex items-center gap-3">
                  <Loader2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-500 animate-spin" />
                  <span className="text-[10px] font-mono text-stone-500 dark:text-stone-500 uppercase tracking-tighter">Executing_Neural_Sequence...</span>
                </div>
              </div>
            )}
          </div>

          {/* Input Interface */}
          <form onSubmit={handleSubmit} className="mt-6 flex gap-2">
            <div className="flex-1 relative">
              <input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Enter command payload..."
                aria-label="Message the TodoFlow assistant"
                disabled={isLoading}
                className="w-full bg-stone-100 dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] px-4 py-3 text-sm text-stone-900 dark:text-white focus:outline-none focus:border-emerald-600/60 transition-colors placeholder:text-stone-500 placeholder:font-mono placeholder:text-[10px] placeholder:uppercase placeholder:tracking-widest"
              />
              <div aria-hidden="true" className="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] font-mono text-stone-400 dark:text-stone-600">
                UTF-8
              </div>
            </div>
            <button
              type="submit"
              aria-label="Send message"
              disabled={isLoading || !inputValue.trim() || !isAuthenticated || !user}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-stone-200 disabled:text-stone-400 dark:disabled:bg-stone-900 dark:disabled:text-stone-700 text-[#0a0a0a] font-bold rounded-[4px] px-4 min-h-11 transition-all active:scale-95 flex items-center justify-center"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CompactChatWidget;