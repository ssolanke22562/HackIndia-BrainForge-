import React, { useState, useRef } from 'react';
import { UploadCloud, Globe, Edit3, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { apiUrl } from '../config/api.ts';

interface DropzoneProps {
  onCaptureComplete: (noteId: string) => void;
}

export const Dropzone: React.FC<DropzoneProps> = ({ onCaptureComplete }) => {
  const [activeMode, setActiveMode] = useState<'upload' | 'link' | 'note'>('upload');
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusType, setStatusType] = useState<'info' | 'success' | 'error'>('info');

  // Link & Note inputs
  const [urlInput, setUrlInput] = useState('');
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  const processPipeline = async (noteId: string) => {
    try {
      // 1. Trigger Classification
      setStatusMessage('Classifying into PARA Framework...');
      await fetch(apiUrl('/classify'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note_id: noteId })
      });

      // 2. Trigger Auto-Linking & Embeddings
      setStatusMessage('Generating embeddings & semantic links...');
      await fetch(apiUrl('/link'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note_id: noteId })
      });

      setStatusType('success');
      setStatusMessage('Successfully ingested, classified, and indexed!');
      onCaptureComplete(noteId);
    } catch (err: any) {
      loggerError('Pipeline background execution warning: ' + err);
    } finally {
      setIsProcessing(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const loggerError = (msg: string) => {
    console.warn(msg);
  };

  const handleFileUpload = async (file: File) => {
    setIsProcessing(true);
    setStatusType('info');
    setStatusMessage(`Uploading & parsing ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(apiUrl('/capture/upload'), {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await res.json();
      if (data.status === 'DUPLICATE_IDENTIFIED') {
        setStatusType('info');
        setStatusMessage(`File recognized as existing note: "${data.title}"`);
        setIsProcessing(false);
        return;
      }

      await processPipeline(data.id);
    } catch (err: any) {
      setStatusType('error');
      setStatusMessage(err.message || 'Failed to ingest file.');
      setIsProcessing(false);
    }
  };

  const handleLinkSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setIsProcessing(true);
    setStatusType('info');
    setStatusMessage('Fetching web readability markdown...');

    try {
      const res = await fetch(apiUrl('/capture/link'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput.trim() })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Web article fetch failed');
      }

      const data = await res.json();
      setUrlInput('');
      await processPipeline(data.id);
    } catch (err: any) {
      setStatusType('error');
      setStatusMessage(err.message || 'Failed to capture URL.');
      setIsProcessing(false);
    }
  };

  const handleNoteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteContent.trim()) return;

    setIsProcessing(true);
    setStatusType('info');
    setStatusMessage('Capturing scratchpad note...');

    try {
      const res = await fetch(apiUrl('/capture/note'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: noteTitle.trim() || undefined,
          content: noteContent.trim()
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Note capture failed');
      }

      const data = await res.json();
      setNoteTitle('');
      setNoteContent('');
      await processPipeline(data.id);
    } catch (err: any) {
      setStatusType('error');
      setStatusMessage(err.message || 'Failed to capture note.');
      setIsProcessing(false);
    }
  };

  return (
    <div className="capture-box glass-panel">
      {/* Mode Tabs */}
      <div className="tab-pills" style={{ marginBottom: 20 }}>
        <button
          className={`tab-pill ${activeMode === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveMode('upload')}
        >
          <UploadCloud size={16} /> File Upload
        </button>
        <button
          className={`tab-pill ${activeMode === 'link' ? 'active' : ''}`}
          onClick={() => setActiveMode('link')}
        >
          <Globe size={16} /> Web Bookmark
        </button>
        <button
          className={`tab-pill ${activeMode === 'note' ? 'active' : ''}`}
          onClick={() => setActiveMode('note')}
        >
          <Edit3 size={16} /> Quick Scratchpad
        </button>
      </div>

      {/* Mode 1: File Dropzone */}
      {activeMode === 'upload' && (
        <div
          className={`dropzone-area ${isDragging ? 'dragging' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files?.[0]) {
              handleFileUpload(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files?.[0]) {
                handleFileUpload(e.target.files[0]);
              }
            }}
          />
          <div className="dropzone-icon">
            <UploadCloud size={32} />
          </div>
          <h3 style={{ fontSize: '1.15rem', marginBottom: 6 }}>
            Drop PDFs, DOCX, Images, Voice Memos, or CSVs here
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Or click to browse from your device
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
            {['PDF', 'DOCX', 'PNG/JPG', 'AUDIO', 'CSV', 'MD'].map((fmt) => (
              <span key={fmt} className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)' }}>
                {fmt}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Mode 2: Web Link Fetcher */}
      {activeMode === 'link' && (
        <form onSubmit={handleLinkSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Web Article or Documentation URL
            </label>
            <input
              type="url"
              className="input-field"
              placeholder="https://example.com/blog/deep-learning-insights"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={isProcessing}>
            {isProcessing ? <Loader2 size={16} className="animate-spin" /> : <Globe size={16} />}
            Fetch & Ingest Article
          </button>
        </form>
      )}

      {/* Mode 3: Quick Scratchpad */}
      {activeMode === 'note' && (
        <form onSubmit={handleNoteSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <input
              type="text"
              className="input-field"
              placeholder="Note Title (optional)"
              value={noteTitle}
              onChange={(e) => setNoteTitle(e.target.value)}
            />
          </div>
          <div>
            <textarea
              className="input-field"
              rows={4}
              placeholder="Type or paste your raw notes, action items, or references..."
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={isProcessing}>
            {isProcessing ? <Loader2 size={16} className="animate-spin" /> : <Edit3 size={16} />}
            Save & Categorize Note
          </button>
        </form>
      )}

      {/* Real-time Status Alert */}
      {statusMessage && (
        <div
          style={{
            marginTop: 16,
            padding: '10px 14px',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            fontSize: '0.875rem',
            background: statusType === 'error' ? 'rgba(239, 68, 68, 0.15)' : statusType === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(139, 92, 246, 0.15)',
            border: `1px solid ${statusType === 'error' ? 'var(--accent-red)' : statusType === 'success' ? 'var(--accent-emerald)' : 'var(--accent-violet)'}`,
            color: statusType === 'error' ? 'var(--accent-red)' : statusType === 'success' ? 'var(--accent-emerald)' : 'var(--accent-violet)'
          }}
        >
          {isProcessing ? (
            <Loader2 size={16} className="animate-spin" />
          ) : statusType === 'success' ? (
            <CheckCircle size={16} />
          ) : (
            <AlertCircle size={16} />
          )}
          <span>{statusMessage}</span>
        </div>
      )}
    </div>
  );
};
