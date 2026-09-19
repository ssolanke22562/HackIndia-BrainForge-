import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, BookOpen, Loader2, ToggleLeft, ToggleRight } from 'lucide-react';
import { CitationModal } from './CitationModal.tsx';
import { apiUrl } from '../config/api.ts';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Array<{
    note_id: string;
    title: string;
    snippet: string;
    score?: number;
    category?: string;
    source_type?: string;
  }>;
}

interface ChatBoxProps {
  sessionId?: string;
  onSessionCreated?: (sessionId: string) => void;
}

export const ChatBox: React.FC<ChatBoxProps> = ({ sessionId, onSessionCreated }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-msg',
      role: 'assistant',
      content: 'Hello! I am your SecondSelf AI Second Brain. Ask me anything across your captured notes, documents, voice memos, and bookmarks.'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(sessionId);
  const [selectedCitation, setSelectedCitation] = useState<any | null>(null);
  const [personaInfo, setPersonaInfo] = useState<{ is_enabled: boolean; name: string; tone: string }>({
    is_enabled: true,
    name: 'You',
    tone: 'Direct & Concise'
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load Persona Settings
  useEffect(() => {
    fetch(apiUrl('/persona'))
      .then((res) => res.json())
      .then((data) => {
        if (data) {
          setPersonaInfo({
            is_enabled: Boolean(data.is_enabled),
            name: data.name || 'You',
            tone: data.communication_tone || 'Direct & Concise'
          });
        }
      })
      .catch((err) => console.debug('Could not load persona in chat:', err));
  }, []);

  const togglePersonaVoice = async () => {
    const nextState = !personaInfo.is_enabled;
    setPersonaInfo((prev) => ({ ...prev, is_enabled: nextState }));
    try {
      await fetch(apiUrl('/persona'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_enabled: nextState })
      });
    } catch (e) {
      console.warn('Failed to update persona toggle:', e);
    }
  };

  // Load existing session thread if sessionId provided
  useEffect(() => {
    if (sessionId) {
      setActiveSessionId(sessionId);
      fetch(apiUrl(`/history/${sessionId}`))
        .then((res) => res.json())
        .then((data) => {
          if (data.messages && data.messages.length > 0) {
            setMessages(data.messages);
          }
        })
        .catch((err) => console.error('Failed to load session:', err));
    }
  }, [sessionId]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuestion = input.trim();
    const userMsgId = 'msg-' + Date.now();
    setInput('');

    const newMessages: Message[] = [
      ...messages,
      { id: userMsgId, role: 'user', content: userQuestion }
    ];
    setMessages(newMessages);
    setLoading(true);

    try {
      const res = await fetch(apiUrl('/ask'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userQuestion,
          session_id: activeSessionId
        })
      });

      if (!res.ok) {
        throw new Error('Failed to retrieve answer');
      }

      const data = await res.json();
      if (!activeSessionId && data.session_id) {
        setActiveSessionId(data.session_id);
        onSessionCreated?.(data.session_id);
      }

      setMessages([
        ...newMessages,
        {
          id: 'asst-' + Date.now(),
          role: 'assistant',
          content: data.answer,
          citations: data.citations
        }
      ]);
    } catch (err: any) {
      setMessages([
        ...newMessages,
        {
          id: 'err-' + Date.now(),
          role: 'assistant',
          content: 'Sorry, I encountered an error searching your knowledge base. Please make sure the backend is connected.'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const renderMessageContent = (msg: Message) => {
    // Replace [Note: <id>] with interactive pill
    const parts = msg.content.split(/(\[Note:\s*[^\]]+\])/g);

    return (
      <div style={{ lineHeight: 1.6 }}>
        {parts.map((part, idx) => {
          const match = part.match(/\[Note:\s*([^\]]+)\]/);
          if (match) {
            const noteIdOrTitle = match[1].trim();
            // Find citation in message metadata if available
            const foundCit = msg.citations?.find((c) => c.note_id.includes(noteIdOrTitle) || noteIdOrTitle.includes(c.note_id.slice(0, 8)));
            
            return (
              <span
                key={idx}
                className="citation-pill"
                onClick={() => {
                  if (foundCit) {
                    setSelectedCitation(foundCit);
                  } else {
                    setSelectedCitation({
                      note_id: noteIdOrTitle,
                      title: `Note ${noteIdOrTitle.slice(0, 8)}`,
                      snippet: 'Cited source reference from your knowledge vault.'
                    });
                  }
                }}
              >
                <BookOpen size={11} style={{ marginRight: 4 }} />
                Note: {noteIdOrTitle.slice(0, 8)}
              </span>
            );
          }
          return <span key={idx}>{part}</span>;
        })}
      </div>
    );
  };

  return (
    <div className="chat-container glass-panel">
      {/* Persona Voice Status Bar */}
      <div style={{
        padding: '10px 18px',
        background: personaInfo.is_enabled ? 'rgba(139, 92, 246, 0.12)' : 'rgba(255, 255, 255, 0.03)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '0.82rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sparkles size={16} color={personaInfo.is_enabled ? 'var(--accent-violet)' : 'var(--text-muted)'} />
          <span>
            {personaInfo.is_enabled ? (
              <>
                <strong style={{ color: 'var(--accent-violet)' }}>SecondSelf Voice:</strong> Speaking as <em>{personaInfo.name}</em> ({personaInfo.tone})
              </>
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>Neutral AI Assistant Mode</span>
            )}
          </span>
        </div>

        <button
          type="button"
          onClick={togglePersonaVoice}
          title="Toggle Personalized SecondSelf Voice"
          style={{
            background: 'none',
            border: 'none',
            color: personaInfo.is_enabled ? 'var(--accent-violet)' : 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: '0.78rem',
            fontWeight: 600
          }}
        >
          {personaInfo.is_enabled ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
          {personaInfo.is_enabled ? 'Voice Active' : 'Enable Voice'}
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="chat-messages-box">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-message-row ${msg.role === 'user' ? 'user-row' : 'assistant-row'}`}
          >
            <div className={`chat-avatar ${msg.role === 'user' ? 'user-avatar' : 'asst-avatar'}`}>
              {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={`chat-bubble ${msg.role === 'user' ? 'user-bubble' : 'asst-bubble'}`}>
              {renderMessageContent(msg)}

              {/* Citations Footer */}
              {msg.citations && msg.citations.length > 0 && (
                <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Sparkles size={12} color="var(--accent-violet)" />
                    Grounded Source Citations:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {msg.citations.map((c, i) => (
                      <button
                        key={i}
                        className="citation-pill"
                        onClick={() => setSelectedCitation(c)}
                      >
                        📄 {c.title} ({( (c.score || 0.8) * 100).toFixed(0)}%)
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-message-row assistant-row">
            <div className="chat-avatar asst-avatar">
              <Bot size={16} />
            </div>
            <div className="chat-bubble asst-bubble" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Loader2 size={16} className="animate-spin" />
              <span>Retrieving from FAISS & FTS5 and synthesizing grounded answer...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSend} className="chat-input-area">
        <input
          type="text"
          className="input-field"
          placeholder="Ask anything about your notes, PDFs, bookmarks, or recordings..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
          <Send size={16} />
        </button>
      </form>

      {/* Citation Inspector Modal */}
      <CitationModal
        isOpen={Boolean(selectedCitation)}
        onClose={() => setSelectedCitation(null)}
        citation={selectedCitation}
      />
    </div>
  );
};
