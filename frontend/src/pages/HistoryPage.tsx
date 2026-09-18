import React, { useState, useEffect } from 'react';
import { MessageSquare, Trash2, ArrowRight, RefreshCw, BookOpen } from 'lucide-react';
import { CitationModal } from '../components/CitationModal.tsx';

export const HistoryPage: React.FC = () => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [followUpInput, setFollowUpInput] = useState('');
  const [answering, setAnswering] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<any | null>(null);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const res = await fetch('/history');
      if (res.ok) {
        const text = await res.text();
        if (text) {
          const data = JSON.parse(text);
          if (Array.isArray(data)) {
            setSessions(data);
            if (data.length > 0 && !selectedSession) {
              fetchSessionThread(data[0].id);
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessionThread = async (sessionId: string) => {
    try {
      const res = await fetch(`/history/${sessionId}`);
      if (res.ok) {
        const text = await res.text();
        if (text) {
          const data = JSON.parse(text);
          setSelectedSession(data);
        }
      }
    } catch (err) {
      console.error('Failed to load thread:', err);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/history/${sessionId}`, { method: 'DELETE' });
      if (res.ok) {
        setSessions(sessions.filter((s) => s.id !== sessionId));
        if (selectedSession?.id === sessionId) {
          setSelectedSession(null);
        }
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleContinueThread = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!followUpInput.trim() || !selectedSession || answering) return;

    const question = followUpInput.trim();
    setFollowUpInput('');
    setAnswering(true);

    try {
      const res = await fetch(`/history/${selectedSession.id}/continue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });
      if (res.ok) {
        await fetchSessionThread(selectedSession.id);
      }
    } catch (err) {
      console.error('Failed to continue conversation:', err);
    } finally {
      setAnswering(false);
    }
  };

  return (
    <div style={{ display: 'flex', gap: 24, height: 'calc(100vh - 120px)' }}>
      {/* Session Sidebar */}
      <div className="glass-panel" style={{ width: 340, display: 'flex', flexDirection: 'column', padding: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <MessageSquare size={18} color="var(--accent-violet)" />
            Chat Sessions ({sessions.length})
          </h2>
          <button className="btn-icon" onClick={fetchSessions} title="Refresh sessions">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {sessions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 8px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No chat history yet. Ask a question in the "Ask Brain" tab to start a thread.
            </div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => fetchSessionThread(s.id)}
                style={{
                  padding: '12px 14px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  background: selectedSession?.id === s.id ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${selectedSession?.id === s.id ? 'var(--accent-violet)' : 'var(--border-subtle)'}`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all 0.15s'
                }}
              >
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {s.title}
                  </h4>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {s.message_count} messages • {s.updated_at ? new Date(s.updated_at).toLocaleDateString() : 'Recent'}
                  </p>
                </div>
                <button
                  className="btn-icon"
                  style={{ color: 'var(--text-muted)' }}
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  title="Delete session"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Conversation Thread View */}
      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {selectedSession ? (
          <>
            <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-subtle)' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{selectedSession.title}</h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Session ID: <code>{selectedSession.id}</code>
              </span>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
              {selectedSession.messages?.map((msg: any) => (
                <div
                  key={msg.id}
                  className={`chat-message-row ${msg.role === 'user' ? 'user-row' : 'assistant-row'}`}
                >
                  <div className={`chat-bubble ${msg.role === 'user' ? 'user-bubble' : 'asst-bubble'}`}>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                      {msg.content}
                    </div>

                    {msg.citations && msg.citations.length > 0 && (
                      <div style={{ marginTop: 12, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
                          Cited Sources:
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {msg.citations.map((c: any, idx: number) => (
                            <button
                              key={idx}
                              className="citation-pill"
                              onClick={() => setSelectedCitation(c)}
                            >
                              <BookOpen size={11} style={{ marginRight: 4 }} />
                              {c.title}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Continue Thread Input */}
            <form onSubmit={handleContinueThread} className="chat-input-area">
              <input
                type="text"
                className="input-field"
                placeholder="Ask follow-up question in this conversation..."
                value={followUpInput}
                onChange={(e) => setFollowUpInput(e.target.value)}
                disabled={answering}
              />
              <button type="submit" className="btn btn-primary" disabled={answering || !followUpInput.trim()}>
                <ArrowRight size={16} />
              </button>
            </form>
          </>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
            <MessageSquare size={48} opacity={0.3} style={{ marginBottom: 12 }} />
            <p>Select a session on the left to review past conversations and grounded citations.</p>
          </div>
        )}
      </div>

      <CitationModal
        isOpen={Boolean(selectedCitation)}
        onClose={() => setSelectedCitation(null)}
        citation={selectedCitation}
      />
    </div>
  );
};
