import React from 'react';
import { Upload, Share2, MessageSquare, History, Database, User } from 'lucide-react';

interface NavbarProps {
  activeTab: 'capture' | 'graph' | 'ask' | 'history' | 'persona';
  setActiveTab: (tab: 'capture' | 'graph' | 'ask' | 'history' | 'persona') => void;
  stats?: {
    notes_count: number;
    links_count: number;
  };
  serverStatus?: 'healthy' | 'offline' | 'checking';
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  stats = { notes_count: 0, links_count: 0 },
  serverStatus = 'checking',
}) => {
  return (
    <header className="navbar">
      <div className="nav-brand">
        <div style={{
          width: 34,
          height: 34,
          borderRadius: 8,
          background: 'linear-gradient(135deg, #8b5cf6, #06b6d4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 12px rgba(139, 92, 246, 0.4)'
        }}>
          <Share2 size={20} color="#ffffff" />
        </div>
        <span>Second<span className="nav-brand-gradient">Self</span></span>
      </div>

      <nav className="nav-links">
        <button
          className={`nav-pill ${activeTab === 'persona' ? 'active' : ''}`}
          onClick={() => setActiveTab('persona')}
        >
          <User size={16} />
          <span>My Voice</span>
        </button>
        <button
          className={`nav-pill ${activeTab === 'capture' ? 'active' : ''}`}
          onClick={() => setActiveTab('capture')}
        >
          <Upload size={16} />
          <span>Capture</span>
        </button>
        <button
          className={`nav-pill ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => setActiveTab('graph')}
        >
          <Share2 size={16} />
          <span>Knowledge Graph</span>
        </button>
        <button
          className={`nav-pill ${activeTab === 'ask' ? 'active' : ''}`}
          onClick={() => setActiveTab('ask')}
        >
          <MessageSquare size={16} />
          <span>Ask Brain</span>
        </button>
        <button
          className={`nav-pill ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          <History size={16} />
          <span>History</span>
        </button>
      </nav>

      <div className="nav-stats">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Database size={14} color="var(--accent-cyan)" />
            <span>{stats.notes_count} Notes</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Share2 size={14} color="var(--accent-violet)" />
            <span>{stats.links_count} Links</span>
          </div>
        </div>

        <div className="status-badge">
          <div className="status-pulse" />
          <span>{serverStatus === 'healthy' ? 'Engine Ready' : 'Connecting'}</span>
        </div>
      </div>
    </header>
  );
};
