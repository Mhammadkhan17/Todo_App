'use client';

import React from 'react';
import { Plus, MessageSquare, Loader2 } from 'lucide-react';
import { cn, formatTaskTimeAgo } from '@/lib/utils';

export interface RagSession {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

interface SessionSidebarProps {
  sessions: RagSession[];
  activeId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
}

const groupLabelFor = (iso?: string): string => {
  if (!iso) return 'Earlier';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Earlier';
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfDate = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate()
  );
  const days = Math.round(
    (startOfToday.getTime() - startOfDate.getTime()) / 86_400_000
  );
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days <= 7) return 'Last 7 days';
  return 'Earlier';
};

const groupSessions = (sessions: RagSession[]) => {
  const order: string[] = [];
  const map = new Map<string, RagSession[]>();
  for (const session of sessions) {
    const label = groupLabelFor(session.updated_at || session.created_at);
    if (!map.has(label)) {
      map.set(label, []);
      order.push(label);
    }
    map.get(label)!.push(session);
  }
  return order.map(label => ({ label, items: map.get(label)! }));
};

const SessionSidebar = ({
  sessions,
  activeId,
  loading,
  onSelect,
  onNew,
}: SessionSidebarProps) => {
  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="shrink-0 p-3 border-b border-stone-200 dark:border-stone-800">
        <div className="flex items-center justify-between mb-3">
          <span className="font-mono text-[10px] font-bold uppercase tracking-widest text-stone-500 dark:text-stone-400">
            {'//'} History
          </span>
          <span className="font-mono text-[10px] text-stone-500 dark:text-stone-500">
            {sessions.length}
          </span>
        </div>
        <button
          type="button"
          onClick={onNew}
          className="w-full min-h-11 flex items-center justify-center gap-2 border border-emerald-600/40 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 rounded-[4px] font-mono text-[10px] font-bold uppercase tracking-widest transition-colors"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
          New_Chat
        </button>
      </div>

      {/* Session list */}
      <nav
        aria-label="Conversation history"
        className="flex-1 min-h-0 overflow-y-auto p-2 space-y-1 custom-scrollbar"
      >
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2
              className="h-4 w-4 text-emerald-600 dark:text-emerald-400 animate-spin"
              aria-hidden="true"
            />
          </div>
        ) : sessions.length === 0 ? (
          <p className="px-2 py-6 text-center font-mono text-[10px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
            No conversations yet
          </p>
        ) : (
          groupSessions(sessions).map((group) => (
            <div key={group.label} className="pb-1">
              <p className="px-3 pt-2 pb-1 font-mono text-[9px] font-bold uppercase tracking-widest text-stone-400 dark:text-stone-600">
                {group.label}
              </p>
              <div className="space-y-1">
                {group.items.map((session) => {
                  const active = session.id === activeId;
                  return (
                    <button
                      key={session.id}
                      type="button"
                      onClick={() => onSelect(session.id)}
                      aria-current={active ? 'true' : undefined}
                      className={cn(
                        'w-full text-left px-3 py-2.5 rounded-[4px] border transition-colors',
                        active
                          ? 'border-emerald-600/40 bg-emerald-500/10 border-l-2 border-l-emerald-600'
                          : 'border-transparent hover:bg-stone-100 dark:hover:bg-[#141414]'
                      )}
                    >
                      <div className="flex items-start gap-2">
                        <MessageSquare
                          className={cn(
                            'h-3.5 w-3.5 mt-0.5 shrink-0',
                            active
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-stone-400 dark:text-stone-600'
                          )}
                          aria-hidden="true"
                        />
                        <div className="min-w-0 flex-1">
                          <p
                            className={cn(
                              'text-xs truncate',
                              active
                                ? 'text-stone-900 dark:text-white font-medium'
                                : 'text-stone-700 dark:text-stone-300'
                            )}
                          >
                            {session.title || 'Untitled'}
                          </p>
                          {(session.updated_at || session.created_at) && (
                            <p className="mt-0.5 font-mono text-[9px] uppercase tracking-widest text-stone-500 dark:text-stone-500">
                              {formatTaskTimeAgo(
                                session.updated_at || session.created_at!
                              )}
                            </p>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </nav>
    </div>
  );
};

export default SessionSidebar;
