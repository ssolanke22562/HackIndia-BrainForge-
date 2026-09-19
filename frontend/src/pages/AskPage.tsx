import React, { useState } from 'react';
import { ChatBox } from '../components/ChatBox.tsx';
import { Sparkles, MessageSquare, ShieldCheck, Zap } from 'lucide-react';

export const AskPage: React.FC = () => {
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(() => {
    return localStorage.getItem('secondself_current_session_id') || undefined;
  });

  const handleSessionCreated = (id: string) => {
    setCurrentSessionId(id);
    localStorage.setItem('secondself_current_session_id', id);
  };

  const handleNewChat = () => {
    setCurrentSessionId(undefined);
    localStorage.removeItem('secondself_current_session_id');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1000, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <h1 style={{ fontSize: '1.875rem', fontWeight: 800 }}>Ask Your Second Brain</h1>
            <span className="badge" style={{ background: 'rgba(139, 92, 246, 0.15)', color: 'var(--accent-violet)', border: '1px solid rgba(139, 92, 246, 0.3)' }}>
              <Sparkles size={12} style={{ marginRight: 4 }} /> Hybrid RAG Engine
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)' }}>
            Answers are synthesized strictly from your captured notes and documents with verifiable citations.
          </p>
        </div>

        {currentSessionId && (
          <button
            className="btn btn-secondary"
            onClick={handleNewChat}
            style={{ fontSize: '0.85rem', gap: 6 }}
            title="Start a new conversation thread"
          >
            <MessageSquare size={15} />
            + New Chat Thread
          </button>
        )}
      </div>

      {/* Feature Pills */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        <div className="glass-panel" style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.85rem' }}>
          <ShieldCheck size={18} color="var(--accent-emerald)" />
          <span>Zero-Hallucination Citations</span>
        </div>
        <div className="glass-panel" style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.85rem' }}>
          <Zap size={18} color="var(--accent-cyan)" />
          <span>Dense FAISS + Sparse FTS5 BM25</span>
        </div>
        <div className="glass-panel" style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.85rem' }}>
          <MessageSquare size={18} color="var(--accent-violet)" />
          <span>Multi-Turn Chat Persistence</span>
        </div>
      </div>

      {/* Interactive Chat Area */}
      <ChatBox
        sessionId={currentSessionId}
        onSessionCreated={handleSessionCreated}
        onNewChat={handleNewChat}
      />
    </div>
  );
};
