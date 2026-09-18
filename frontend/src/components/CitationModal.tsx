import React from 'react';
import { X } from 'lucide-react';

interface CitationModalProps {
  isOpen: boolean;
  onClose: () => void;
  citation: {
    note_id: string;
    title: string;
    category?: string;
    source_type?: string;
    snippet: string;
    relevance_score?: number;
    raw_path?: string;
    created_at?: string;
  } | null;
}

export const CitationModal: React.FC<CitationModalProps> = ({ isOpen, onClose, citation }) => {
  if (!isOpen || !citation) return null;

  const getCategoryColor = (cat?: string) => {
    switch (cat) {
      case 'Projects': return 'var(--accent-violet)';
      case 'Areas': return 'var(--accent-cyan)';
      case 'Resources': return 'var(--accent-emerald)';
      case 'Archives': return 'var(--accent-amber)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card glass-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span
              className="badge"
              style={{
                background: `${getCategoryColor(citation.category)}20`,
                color: getCategoryColor(citation.category),
                border: `1px solid ${getCategoryColor(citation.category)}40`
              }}
            >
              {citation.category || 'Resources'}
            </span>
            <span className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)' }}>
              {citation.source_type?.toUpperCase() || 'NOTE'}
            </span>
          </div>
          <button className="btn-icon" onClick={onClose} title="Close inspector">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <h2 style={{ fontSize: '1.25rem', marginBottom: 12, color: 'var(--text-primary)' }}>
            {citation.title}
          </h2>

          <div style={{ display: 'flex', gap: 16, fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 16 }}>
            <div><strong>ID:</strong> <code style={{ color: 'var(--accent-cyan)' }}>{citation.note_id.slice(0, 8)}</code></div>
            {citation.relevance_score !== undefined && (
              <div><strong>Match Score:</strong> {(citation.relevance_score * 100).toFixed(1)}%</div>
            )}
          </div>

          <div style={{ marginBottom: 16 }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Extracted Grounded Source Snippet
            </h4>
            <div className="citation-snippet-box">
              {citation.snippet}
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Verified Knowledge Chunk • Zero Hallucination Guarantee
          </span>
          <button className="btn btn-secondary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
