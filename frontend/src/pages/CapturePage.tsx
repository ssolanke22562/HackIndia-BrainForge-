import React, { useState, useEffect } from 'react';
import { Dropzone } from '../components/Dropzone.tsx';
import { Sparkles, RefreshCw, FileText, CheckCircle2, Clock } from 'lucide-react';
import { apiUrl } from '../config/api.ts';

export const CapturePage: React.FC = () => {
  const [recentNotes, setRecentNotes] = useState<any[]>([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [seedingDemo, setSeedingDemo] = useState(false);

  const fetchRecentCaptures = async () => {
    setLoadingNotes(true);
    try {
      const res = await fetch(apiUrl('/capture?limit=15'));
      if (res.ok) {
        const data = await res.json();
        setRecentNotes(data);
      }
    } catch (err) {
      console.error('Failed to load recent notes:', err);
    } finally {
      setLoadingNotes(false);
    }
  };

  useEffect(() => {
    fetchRecentCaptures();
  }, []);

  const handleSeedDemoData = async () => {
    setSeedingDemo(true);
    try {
      // Create 5 sample demo notes across multiple modalities & categories
      const demoCaptures = [
        {
          type: 'note',
          title: 'SecondSelf Phase 2 Roadmap & Hackathon Milestones',
          content: 'TODO: Complete Phase 2 LLM classifier, integrate FAISS semantic auto-linking, and finalize RAG reciprocal rank fusion before the pitch deadline.'
        },
        {
          type: 'note',
          title: 'Daily Ergonomics & Engineering Fitness Routine',
          content: 'Maintain 30-minute posture breaks, daily hydration tracking, and weekly ergonomic reviews for team health standards.'
        },
        {
          type: 'note',
          title: 'FAISS Vector Indexing & Cosine Distance Cheatsheet',
          content: 'Reference notes on faiss.IndexFlatIP, L2 vector normalization, inner product similarity metrics, and high-dimensional nearest neighbor search.'
        },
        {
          type: 'note',
          title: 'Legacy Server Migration Log 2021',
          content: 'Archived post-mortem log from Q3 2021 database migration from monolith Postgres to decentralized SQLite clusters.'
        }
      ];

      for (const item of demoCaptures) {
        const res = await fetch(apiUrl('/capture/note'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: item.title, content: item.content })
        });
        if (res.ok) {
          const data = await res.json();
          // Classify & link
          await fetch(apiUrl('/classify'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note_id: data.id })
          });
          await fetch(apiUrl('/link'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note_id: data.id })
          });
        }
      }

      await fetchRecentCaptures();
    } catch (err) {
      console.error('Demo seeding error:', err);
    } finally {
      setSeedingDemo(false);
    }
  };

  const getCategoryClass = (cat?: string) => {
    switch (cat) {
      case 'Projects': return 'badge-projects';
      case 'Areas': return 'badge-areas';
      case 'Resources': return 'badge-resources';
      case 'Archives': return 'badge-archives';
      default: return '';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 800, marginBottom: 6 }}>
            Capture Studio
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Ingest heterogeneous multi-modal inputs. SecondSelf automatically normalizes, classifies via PARA, and links into your knowledge graph.
          </p>
        </div>

        <button
          className="btn btn-secondary"
          onClick={handleSeedDemoData}
          disabled={seedingDemo}
          style={{ gap: 8 }}
        >
          <Sparkles size={16} color="var(--accent-violet)" />
          {seedingDemo ? 'Seeding Demo Notes...' : 'Load Demo Knowledge Base'}
        </button>
      </div>

      {/* Main Ingestion Dropzone */}
      <Dropzone onCaptureComplete={() => fetchRecentCaptures()} />

      {/* Recent Captures Feed */}
      <div className="glass-panel" style={{ padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Clock size={18} color="var(--accent-cyan)" />
            Recent Knowledge Captures ({recentNotes.length})
          </h2>
          <button className="btn-icon" onClick={fetchRecentCaptures} title="Refresh captures">
            <RefreshCw size={16} className={loadingNotes ? 'animate-spin' : ''} />
          </button>
        </div>

        {recentNotes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>
            <FileText size={36} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
            <p>No captures found yet. Drop a file above or click "Load Demo Knowledge Base".</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {recentNotes.map((note) => (
              <div
                key={note.id}
                style={{
                  padding: '14px 18px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 10,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 16,
                  transition: 'background 0.2s'
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <h3 style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {note.title}
                    </h3>
                    {note.category && (
                      <span className={`badge-para ${getCategoryClass(note.category)}`}>
                        {note.category}
                      </span>
                    )}
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>
                      {note.source_type?.toUpperCase()}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineClamp: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {note.summary || 'Extracted raw knowledge capture.'}
                  </p>
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right' }}>
                  <div style={{ color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <CheckCircle2 size={12} /> {note.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
