'use client';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Input from '@/components/Input';
import Textarea from '@/components/Textarea';
import Select from '@/components/Select';
import LinkedInPreview from '@/components/LinkedInPreview';
import ProgressStream from '@/components/ProgressStream';
import { API_URL } from '@/lib/constants';
import { savePost } from '@/lib/api';

const TONES = [
  { value: 'professional', label: 'Professional' },
  { value: 'thought-leader', label: 'Thought Leader' },
  { value: 'educational', label: 'Educational' },
  { value: 'storytelling', label: 'Storytelling' },
  { value: 'casual', label: 'Casual' }
];

const LINKEDIN_PROFILE_KEY = 'linkedin_profile_url';

function LinkedInProfileBadge({ profileUrl, onEdit }) {
  if (!profileUrl) return null;
  const handle = profileUrl.replace(/https?:\/\/(www\.)?linkedin\.com\/in\/?/i, '').replace(/\/$/, '');
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '8px',
      background: '#EBF5FB', border: '1px solid #B3D4F5',
      borderRadius: '8px', padding: '6px 12px', fontSize: '13px', color: '#1a5276'
    }}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="#0077B5"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
      <span>Connected as <strong>in/{handle}</strong></span>
      <button onClick={onEdit} style={{
        background: 'none', border: 'none', cursor: 'pointer',
        color: '#0077B5', fontSize: '12px', textDecoration: 'underline', padding: 0
      }}>Change</button>
    </div>
  );
}

function ProfileSetupModal({ onSave, onSkip, existing }) {
  const [url, setUrl] = useState(existing || '');
  const [error, setError] = useState('');

  const validate = (val) => {
    if (!val) return 'Please enter your LinkedIn profile URL.';
    if (!/linkedin\.com\/in\//i.test(val)) return 'Must be a LinkedIn profile URL (e.g. https://www.linkedin.com/in/yourname)';
    return '';
  };

  const handleSave = () => {
    const err = validate(url.trim());
    if (err) { setError(err); return; }
    onSave(url.trim());
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
    }}>
      <div style={{
        background: '#fff', borderRadius: '16px', padding: '32px',
        width: '460px', boxShadow: '0 20px 60px rgba(0,0,0,0.18)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div style={{
            background: '#0077B5', borderRadius: '8px', width: '36px', height: '36px',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '16px', color: '#1a1a1a' }}>Connect your LinkedIn</div>
            <div style={{ fontSize: '12px', color: '#666' }}>Used for publishing & post preview</div>
          </div>
        </div>

        <label style={{ display: 'block', fontWeight: 600, fontSize: '13px', color: '#333', marginBottom: '6px' }}>
          Your LinkedIn Profile URL
        </label>
        <input
          type="url"
          placeholder="https://www.linkedin.com/in/yourname"
          value={url}
          onChange={e => { setUrl(e.target.value); setError(''); }}
          onKeyDown={e => e.key === 'Enter' && handleSave()}
          style={{
            width: '100%', boxSizing: 'border-box', padding: '10px 14px',
            border: error ? '1.5px solid #e74c3c' : '1.5px solid #ddd',
            borderRadius: '8px', fontSize: '14px', outline: 'none',
            fontFamily: 'monospace', letterSpacing: '0.02em'
          }}
          autoFocus
        />
        {error && <div style={{ color: '#e74c3c', fontSize: '12px', marginTop: '5px' }}>{error}</div>}

        <div style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
          Find it at <a href="https://www.linkedin.com/in/" target="_blank" rel="noreferrer" style={{ color: '#0077B5' }}>linkedin.com/in/your-name</a>. This is saved in your browser only.
        </div>

        <div style={{ display: 'flex', gap: '10px', marginTop: '24px' }}>
          <button onClick={handleSave} style={{
            flex: 1, background: '#0077B5', color: '#fff', border: 'none',
            borderRadius: '8px', padding: '11px', fontWeight: 600, fontSize: '14px',
            cursor: 'pointer'
          }}>Save Profile</button>
          <button onClick={onSkip} style={{
            padding: '11px 18px', background: 'none', border: '1.5px solid #ddd',
            borderRadius: '8px', fontSize: '14px', cursor: 'pointer', color: '#666'
          }}>Skip for now</button>
        </div>
      </div>
    </div>
  );
}

export default function CreatePage() {
  const searchParams = useSearchParams();
  const [formData, setFormData] = useState({ title: '', topic: '', audience: '', tone: 'professional' });
  const [postData, setPostData] = useState({ content: '', hashtags: [], cta: '' });
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState([]);
  const [error, setError] = useState('');
  const [profileUrl, setProfileUrl] = useState('');
  const [showProfileModal, setShowProfileModal] = useState(false);

  useEffect(() => {
    const saved = typeof window !== 'undefined' ? localStorage.getItem(LINKEDIN_PROFILE_KEY) : '';
    setProfileUrl(saved || '');
    if (!saved) {
      setShowProfileModal(true);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Check URL params
    const topic = searchParams.get('topic');
    if (topic) {
      setFormData((p) => ({ ...p, topic: decodeURIComponent(topic) }));
      return;
    }

    // Check localStorage for prefilled data from suggestions
    const prefillTopic = localStorage.getItem('prefill_topic');
    const prefillHook = localStorage.getItem('prefill_hook');
    if (prefillTopic) {
      setFormData((p) => ({
        ...p,
        topic: prefillTopic,
        title: prefillHook || '',
      }));
      // Clear the prefill data
      localStorage.removeItem('prefill_topic');
      localStorage.removeItem('prefill_hook');
    }
  }, [searchParams]);

  const saveProfile = (url) => {
    localStorage.setItem(LINKEDIN_PROFILE_KEY, url);
    setProfileUrl(url);
    setShowProfileModal(false);
  };

  const onChange = (e) => setFormData((p) => ({ ...p, [e.target.name]: e.target.value }));
  const gen = async () => {
    if (!formData.topic.trim()) {
      setError('Please enter a topic');
      return;
    }
    setBusy(true);
    setProgress([]);
    setError('');
    try {
      const payload = {
        topic: formData.topic.trim(),
        audience: (formData.audience || '').trim() || 'general',
        tone: formData.tone || 'professional',
        objective: 'engagement',
        min_chars: 500,
        max_chars: 1800,
      };
      const res = await fetch(`${API_URL}/api/posts/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify(payload),
      });
      if (!res.ok || !res.body) {
        const errText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errText}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';
        for (const evt of events) {
          const line = evt.split('\n').find((l) => l.startsWith('data: '));
          if (!line) continue;
          try {
            const data = JSON.parse(line.slice(6));
            setProgress((prev) => [...prev, data]);
            if (data.stage === 'complete' && data.status === 'success') {
              setPostData({
                content: data.data?.content || '',
                hashtags: data.data?.hashtags || [],
                cta: data.data?.cta || '',
              });
            }
            if (data.stage === 'error') setError(data.message || 'Generation failed');
          } catch (parseErr) {
            console.error('Failed to parse SSE event:', parseErr, line);
          }
        }
      }
    } catch (e) {
      setError(e.message || 'Failed to generate');
    } finally {
      setBusy(false);
    }
  };
  const save = async () => {
    setBusy(true);
    await savePost({ ...formData, ...postData, status: 'draft', title: formData.title || formData.topic });
    window.location.href = '/publish';
  };

  return (
    <div>
      {showProfileModal && (
        <ProfileSetupModal
          existing={profileUrl}
          onSave={saveProfile}
          onSkip={() => setShowProfileModal(false)}
        />
      )}
      <div style={{ paddingBottom: '12px', borderBottom: '1px solid #e8ecef', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '22px', fontWeight: 700, color: '#1a1a1a' }}>LinkedIn Post Generator</h1>
        <LinkedInProfileBadge profileUrl={profileUrl} onEdit={() => setShowProfileModal(true)} />
      </div>
      <a href="https://www.linkedin.com/article/newsletter/new/" target="_blank" rel="noreferrer" style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        background: 'linear-gradient(90deg, #0077B5 0%, #00a0dc 100%)',
        color: '#fff', borderRadius: '10px', padding: '12px 18px',
        textDecoration: 'none', marginBottom: '24px',
        boxShadow: '0 2px 10px rgba(0,119,181,0.25)'
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="white"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
        <div>
          <div style={{ fontWeight: 700, fontSize: '14px' }}>Start a LinkedIn Newsletter Article</div>
          <div style={{ fontSize: '12px', opacity: 0.85 }}>linkedin.com/article/newsletter/new/ →</div>
        </div>
      </a>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <Card><Input label="Title" name="title" value={formData.title} onChange={onChange} /><Textarea label="Topic" name="topic" value={formData.topic} onChange={onChange} /><Input label="Audience" name="audience" value={formData.audience} onChange={onChange} /><Select label="Tone" name="tone" value={formData.tone} onChange={onChange} options={TONES} /><Button onClick={gen} disabled={busy || !formData.topic.trim()} variant="primary">{busy ? 'Generating...' : 'Generate'}</Button>{error && <div className="mt-3 text-sm text-red-700">{error}</div>}</Card>
          {busy && <ProgressStream progress={progress} />}
          {postData.content && <Card><Textarea label="Content" value={postData.content} onChange={(e)=>setPostData((p)=>({...p,content:e.target.value}))} rows={8} /><Input label="Hashtags" value={postData.hashtags.join(' ')} onChange={(e)=>setPostData((p)=>({...p,hashtags:e.target.value.split(' ').filter(Boolean)}))} /><Input label="CTA" value={postData.cta} onChange={(e)=>setPostData((p)=>({...p,cta:e.target.value}))} /><div style={{ display: 'flex', gap: '10px' }}><Button onClick={save} disabled={busy} variant="primary">Save Draft</Button><a href="https://www.linkedin.com/article/newsletter/new/" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: '#0077B5', textDecoration: 'none', fontWeight: 600 }}>📰 Newsletter Article ↗</a></div></Card>}
        </div>
        <LinkedInPreview title={formData.title} content={postData.content} hashtags={postData.hashtags} cta={postData.cta} profileUrl={profileUrl} />
      </div>
    </div>
  );
}
