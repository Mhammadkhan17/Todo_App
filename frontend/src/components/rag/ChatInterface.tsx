'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext'; // Use the custom auth context
import { Send, Bot, FileText, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { user, token, isAuthenticated } = useAuth(); // Get auth info from custom context

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim() || isLoading || !isAuthenticated) return;

    // Add user message
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
      // Call the RAG API
      const response = await fetch('/api/rag/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token || ''}`, // Use token from auth context
        },
        body: JSON.stringify({
          message: inputValue,
          session_id: sessionId || undefined,
          user_id: user?.id?.toString(), // Use user ID from auth context
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Update session ID if it was returned
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      // Add assistant message
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        role: 'assistant',
        timestamp: new Date(),
        sources: data.sources || [],
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        role: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatSourceMetadata = (metadata: Record<string, unknown>) => {
    const { source, file_name, ...other } = metadata;
    const fileName = typeof file_name === 'string' ? file_name : undefined;
    const sourceName = typeof source === 'string' ? source : undefined;
    return (
      <div className="text-[10px] font-mono uppercase tracking-wider text-stone-500 dark:text-stone-500">
        {fileName && <span className="font-bold text-stone-700 dark:text-stone-300">{fileName}</span>}
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
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Chat messages"
        className="flex-1 overflow-y-auto px-4 py-6 bg-stone-50/50 dark:bg-[#0a0a0a] custom-scrollbar scroll-smooth"
      >
        {messages.length === 0 ? (
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
          </div>
        ) : (
          <div className="space-y-6 max-w-3xl mx-auto w-full">
            {messages.map((message) => (
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
                    {message.timestamp.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
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
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
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
                        <FileText className="h-3 w-3 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
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
                            <div className="line-clamp-2 text-stone-600 dark:text-stone-400">{source.content}</div>
                            <div className="mt-1.5">{formatSourceMetadata(source.metadata)}</div>
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
                  <Loader2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-500 animate-spin" aria-hidden="true" />
                  <span className="font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
                    Executing_Sequence...
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Composer */}
      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-stone-200 dark:border-stone-800 bg-white dark:bg-[#0f0f0f] p-4"
      >
        <div className="flex gap-3 max-w-3xl mx-auto w-full">
          <input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Enter_Query_Payload..."
            aria-label="Ask a question about your documents"
            disabled={isLoading}
            className="flex-1 min-h-11 bg-stone-100 dark:bg-[#141414] border border-stone-200 dark:border-stone-800 rounded-[4px] px-4 py-3 text-sm text-stone-900 dark:text-white focus:outline-none focus:border-emerald-600/60 transition-colors placeholder:font-mono placeholder:text-[10px] placeholder:uppercase placeholder:tracking-widest placeholder:text-stone-500 dark:placeholder:text-stone-500 disabled:opacity-60"
          />
          <button
            type="submit"
            aria-label="Send message"
            disabled={isLoading || !inputValue.trim() || !isAuthenticated}
            className="min-h-11 min-w-11 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-stone-200 disabled:text-stone-400 dark:disabled:bg-stone-900 dark:disabled:text-stone-700 text-[#0a0a0a] rounded-[4px] transition-all active:scale-95 flex items-center justify-center"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Send className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>
      </form>
    </>
  );
};

export default ChatInterface;
