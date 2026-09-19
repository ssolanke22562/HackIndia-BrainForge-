import React, { useState, useEffect } from 'react';
import { GraphView } from '../components/GraphView.tsx';
import { Search, RefreshCw, X, Network as NetworkIcon } from 'lucide-react';
import { apiUrl } from '../config/api.ts';

export const GraphPage: React.FC = () => {
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[]; stats?: any }>({ nodes: [], edges: [] });
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedCategory !== 'all') params.append('category', selectedCategory);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());

      const res = await fetch(apiUrl(`/graph?${params.toString()}`));
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
      }
    } catch (err) {
      console.error('Failed to load graph data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, [selectedCategory]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchGraphData();
  };

  const handleNodeClick = (nodeId: string) => {
    const node = graphData.nodes.find((n) => n.id === nodeId);
    if (node) {
      setSelectedNode(node);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: 'calc(100vh - 120px)' }}>
      {/* Control Bar */}
      <div className="glass-panel" style={{ padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <NetworkIcon size={22} color="var(--accent-violet)" />
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Living Knowledge Graph</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {graphData.stats?.total_nodes || graphData.nodes.length} Nodes • {graphData.stats?.total_edges || graphData.edges.length} Semantic Links (τ ≥ 0.70)
            </p>
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {/* Category Tabs */}
          <div className="tab-pills" style={{ margin: 0 }}>
            {['all', 'Projects', 'Areas', 'Resources', 'Archives'].map((cat) => (
              <button
                key={cat}
                className={`tab-pill ${selectedCategory === cat ? 'active' : ''}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: 6 }}>
            <input
              type="text"
              className="input-field"
              placeholder="Search graph..."
              style={{ width: 180, padding: '6px 10px', fontSize: '0.85rem' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button type="submit" className="btn btn-secondary" style={{ padding: '6px 12px' }}>
              <Search size={14} />
            </button>
          </form>

          <button className="btn-icon" onClick={fetchGraphData} title="Re-stabilize graph">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Main Canvas & Side Inspector Layout */}
      <div style={{ display: 'flex', gap: 20, flex: 1, position: 'relative', overflow: 'hidden' }}>
        {/* Canvas Area */}
        <div className="glass-panel" style={{ flex: 1, height: '100%', borderRadius: 12, overflow: 'hidden' }}>
          {graphData.nodes.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', gap: 12 }}>
              <NetworkIcon size={48} opacity={0.3} />
              <p>No nodes found matching filters. Ingest notes in Capture Studio to build the graph.</p>
            </div>
          ) : (
            <GraphView
              nodesData={graphData.nodes}
              edgesData={graphData.edges}
              onSelectNode={handleNodeClick}
            />
          )}
        </div>

        {/* Node Inspector Drawer */}
        {selectedNode && (
          <div
            className="glass-panel"
            style={{
              width: 360,
              padding: 20,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
              overflowY: 'auto',
              borderLeft: '1px solid var(--border-highlight)',
              boxShadow: 'var(--shadow-glow-violet)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span
                className="badge"
                style={{
                  background: `${selectedNode.color?.background || '#8b5cf6'}20`,
                  color: selectedNode.color?.background || 'var(--accent-violet)',
                  border: `1px solid ${selectedNode.color?.background || '#8b5cf6'}40`
                }}
              >
                {selectedNode.category}
              </span>
              <button className="btn-icon" onClick={() => setSelectedNode(null)}>
                <X size={16} />
              </button>
            </div>

            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 8, color: 'var(--text-primary)' }}>
                {selectedNode.full_title || selectedNode.label}
              </h3>
              <div style={{ display: 'flex', gap: 10, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span><strong>Format:</strong> {selectedNode.source_type?.toUpperCase()}</span>
                <span><strong>Connections:</strong> {Math.max(1, Math.round((selectedNode.value - 12) / 4))}</span>
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: 12, borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: 6 }}>
                Summary
              </h4>
              <p style={{ fontSize: '0.85rem', lineHeight: 1.5, color: 'var(--text-secondary)' }}>
                {selectedNode.summary || 'No summary available.'}
              </p>
            </div>

            <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Node ID: <code style={{ color: 'var(--accent-cyan)' }}>{selectedNode.id}</code>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
