import React, { useState, useEffect } from 'react';
import { 
  User, 
  Sparkles, 
  Save, 
  RefreshCw, 
  CheckCircle2, 
  Sliders, 
  FileText, 
  Zap,
  BrainCircuit,
  Briefcase,
  PenTool,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';
import { apiUrl } from '../config/api.ts';

interface PersonaData {
  id?: string;
  name: string;
  role_profession: string;
  communication_tone: string;
  perspective: string;
  custom_vocabulary: string;
  writing_sample: string;
  response_format: string;
  is_enabled: boolean;
}

const TONE_PRESETS = [
  {
    label: 'Direct & Concise',
    icon: Zap,
    tone: 'Direct, technical, and concise with zero fluff',
    format: 'TL;DR summary first, followed by clear bullet points and actionable takeaways'
  },
  {
    label: 'Deep Technical',
    icon: BrainCircuit,
    tone: 'In-depth architectural analysis, rigorous terminology, and tradeoff evaluations',
    format: 'Detailed breakdown with architectural tradeoffs and implementation steps'
  },
  {
    label: 'Executive Summary',
    icon: Briefcase,
    tone: 'High-level, strategic, business impact oriented, and decisive',
    format: 'Executive summary with key metrics, high-level impact, and next steps'
  },
  {
    label: 'Conversational & Engaging',
    icon: PenTool,
    tone: 'Friendly, engaging, witty, and relatable with intuitive analogies',
    format: 'Conversational paragraphs with clear highlights and bold emphasis'
  }
];

export const PersonaPage: React.FC = () => {
  const [formData, setFormData] = useState<PersonaData>({
    name: 'SecondSelf User',
    role_profession: 'Knowledge Worker & Researcher',
    communication_tone: 'Direct, technical, and concise with zero fluff',
    perspective: 'First-Person (I, my)',
    custom_vocabulary: 'tradeoffs, architecture, synthesis, high-leverage, action items',
    writing_sample: '',
    response_format: 'TL;DR summary first, followed by clear bullet points and actionable takeaways',
    is_enabled: true
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [analysisSummary, setAnalysisSummary] = useState<string | null>(null);

  useEffect(() => {
    fetchPersona();
  }, []);

  const fetchPersona = async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/persona'));
      if (res.ok) {
        const data = await res.json();
        setFormData(data);
      }
    } catch (err) {
      console.error('Failed to load persona:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);

    try {
      const res = await fetch(apiUrl('/persona'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        const data = await res.json();
        setFormData(data);
        setSavedSuccess(true);
        setTimeout(() => setSavedSuccess(false), 4000);
      }
    } catch (err) {
      console.error('Failed to save persona:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleAnalyzeSample = async () => {
    if (!formData.writing_sample.trim()) return;
    setAnalyzing(true);
    setAnalysisSummary(null);

    try {
      const res = await fetch(apiUrl('/persona/analyze'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sample_text: formData.writing_sample })
      });

      if (res.ok) {
        const data = await res.json();
        setFormData((prev) => ({
          ...prev,
          communication_tone: data.detected_tone || prev.communication_tone,
          role_profession: data.detected_role || prev.role_profession,
          custom_vocabulary: data.suggested_vocabulary || prev.custom_vocabulary,
          response_format: data.suggested_format || prev.response_format
        }));
        setAnalysisSummary(data.style_summary || 'Analyzed style traits and auto-populated the form!');
      }
    } catch (err) {
      console.error('Failed to analyze sample:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const applyPreset = (preset: typeof TONE_PRESETS[0]) => {
    setFormData((prev) => ({
      ...prev,
      communication_tone: preset.tone,
      response_format: preset.format
    }));
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <RefreshCw size={28} className="animate-spin" color="var(--accent-violet)" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28, maxWidth: 1000, margin: '0 auto', paddingBottom: 40 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 800, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 10 }}>
            <User size={28} color="var(--accent-violet)" />
            SecondSelf Voice & Persona Profile
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Train SecondSelf to speak, reason, and answer in <strong>your exact words and communication style</strong> during RAG synthesis.
          </p>
        </div>

        {/* Master Voice Toggle */}
        <button
          className={`btn ${formData.is_enabled ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => {
            const nextState = !formData.is_enabled;
            setFormData((prev) => ({ ...prev, is_enabled: nextState }));
          }}
          style={{ gap: 10 }}
        >
          {formData.is_enabled ? (
            <>
              <ToggleRight size={22} />
              Personalized Voice: Active
            </>
          ) : (
            <>
              <ToggleLeft size={22} />
              Neutral Assistant Mode
            </>
          )}
        </button>
      </div>

      {/* Success Notification */}
      {savedSuccess && (
        <div style={{
          padding: '14px 20px',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          color: '#10b981',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          fontWeight: 600
        }}>
          <CheckCircle2 size={20} />
          Persona profile saved! SecondSelf will now answer RAG queries in your personalized voice.
        </div>
      )}

      {/* Quick Tone Presets */}
      <div className="glass-panel" style={{ padding: 22 }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sliders size={18} color="var(--accent-cyan)" />
          Quick Tone Presets
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          {TONE_PRESETS.map((p) => {
            const IconComponent = p.icon;
            const isSelected = formData.communication_tone === p.tone;
            return (
              <button
                key={p.label}
                type="button"
                className={`glass-panel ${isSelected ? 'selected-preset' : ''}`}
                onClick={() => applyPreset(p)}
                style={{
                  padding: 14,
                  textAlign: 'left',
                  cursor: 'pointer',
                  border: isSelected ? '1.5px solid var(--accent-violet)' : '1px solid var(--border-glass)',
                  background: isSelected ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, color: isSelected ? 'var(--accent-violet)' : 'var(--text-primary)' }}>
                  <IconComponent size={18} />
                  {p.label}
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {p.tone}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Profile Form */}
      <form onSubmit={handleSave} className="glass-panel" style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
          {/* Name / Handle */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: 6, color: 'var(--text-secondary)' }}>
              Your Name / Alias
            </label>
            <input
              type="text"
              className="input-field"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. Sarthak, Alex, Dev"
              required
            />
          </div>

          {/* Role / Profession */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: 6, color: 'var(--text-secondary)' }}>
              Profession & Domain Expertise
            </label>
            <input
              type="text"
              className="input-field"
              value={formData.role_profession}
              onChange={(e) => setFormData({ ...formData, role_profession: e.target.value })}
              placeholder="e.g. Senior Software Architect & AI Researcher"
              required
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
          {/* Communication Tone */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: 6, color: 'var(--text-secondary)' }}>
              Communication Tone & Personality
            </label>
            <input
              type="text"
              className="input-field"
              value={formData.communication_tone}
              onChange={(e) => setFormData({ ...formData, communication_tone: e.target.value })}
              placeholder="e.g. Direct, technical, concise, pragmatic"
              required
            />
          </div>

          {/* Perspective */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: 6, color: 'var(--text-secondary)' }}>
              Speaking Perspective
            </label>
            <select
              className="input-field"
              value={formData.perspective}
              onChange={(e) => setFormData({ ...formData, perspective: e.target.value })}
            >
              <option value="First-Person (I, my, our)">First-Person (I, my, our) — Speaks as You</option>
              <option value="Second-Person (You, your)">Second-Person (You, your) — Speaks to You</option>
              <option value="Third-Person (Objective & Neutral)">Third-Person (Objective & Neutral)</option>
            </select>
          </div>
        </div>

        {/* Custom Vocabulary / Jargon */}
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: 6, color: 'var(--text-secondary)' }}>
            Signature Vocabulary & Preferred Jargon
          </label>
          <input
            type="text"
            className="input-field"
            value={formData.custom_vocabulary}
            onChange={(e) => setFormData({ ...formData, custom_vocabulary: e.target.value })}
            placeholder="e.g. tradeoffs, architecture, synthesis, high-leverage, action items, latency, scale"
          />
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
            Comma-separated terms you use often. SecondSelf will naturally incorporate these phrases into synthesized answers.
          </p>
        </div>

        {/* Response Format Preference */}
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: 6, color: 'var(--text-secondary)' }}>
            Preferred Response Structure
          </label>
          <input
            type="text"
            className="input-field"
            value={formData.response_format}
            onChange={(e) => setFormData({ ...formData, response_format: e.target.value })}
            placeholder="e.g. TL;DR summary at top, followed by structured bullet points"
            required
          />
        </div>

        {/* Writing Sample Calibration */}
        <div style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <FileText size={16} color="var(--accent-violet)" />
              Your Writing Sample (For Calibration)
            </label>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAnalyzeSample}
              disabled={analyzing || !formData.writing_sample.trim()}
              style={{ padding: '4px 12px', fontSize: '0.75rem', gap: 6 }}
            >
              <Sparkles size={14} color="var(--accent-cyan)" className={analyzing ? 'animate-spin' : ''} />
              {analyzing ? 'Analyzing with AI...' : '✨ Auto-Detect My Style'}
            </button>
          </div>

          <textarea
            className="input-field"
            rows={4}
            value={formData.writing_sample}
            onChange={(e) => setFormData({ ...formData, writing_sample: e.target.value })}
            placeholder="Paste a paragraph of an email, document, or memo you wrote. Our AI will analyze your sentence cadence, tone, and stylistic traits..."
          />

          {analysisSummary && (
            <div style={{
              marginTop: 10,
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              fontSize: '0.8rem',
              color: 'var(--accent-cyan)'
            }}>
              <strong>AI Analysis:</strong> {analysisSummary}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchPersona}
            disabled={saving}
          >
            Reset
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
            style={{ gap: 8, padding: '10px 24px' }}
          >
            <Save size={18} />
            {saving ? 'Saving Persona...' : 'Save & Calibrate Voice'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PersonaPage;
