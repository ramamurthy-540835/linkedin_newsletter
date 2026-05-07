'use client';
import { useState } from 'react';
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

export default function CreatePage() {
  const [formData, setFormData] = useState({ title: '', topic: '', audience: '', tone: 'professional' });
  const [postData, setPostData] = useState({ content: '', hashtags: [], cta: '' });
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState([]);
  const [error, setError] = useState('');

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

  return <div className="grid lg:grid-cols-3 gap-6"><div className="lg:col-span-2 space-y-4"><Card><Input label="Title" name="title" value={formData.title} onChange={onChange} /><Textarea label="Topic" name="topic" value={formData.topic} onChange={onChange} /><Input label="Audience" name="audience" value={formData.audience} onChange={onChange} /><Select label="Tone" name="tone" value={formData.tone} onChange={onChange} options={TONES} /><Button onClick={gen} disabled={busy || !formData.topic.trim()} variant="primary">{busy ? 'Generating...' : 'Generate'}</Button>{error && <div className="mt-3 text-sm text-red-700">{error}</div>}</Card>{busy && <ProgressStream progress={progress} />}{postData.content && <Card><Textarea label="Content" value={postData.content} onChange={(e)=>setPostData((p)=>({...p,content:e.target.value}))} rows={8} /><Input label="Hashtags" value={postData.hashtags.join(' ')} onChange={(e)=>setPostData((p)=>({...p,hashtags:e.target.value.split(' ').filter(Boolean)}))} /><Input label="CTA" value={postData.cta} onChange={(e)=>setPostData((p)=>({...p,cta:e.target.value}))} /><Button onClick={save} disabled={busy} variant="primary">Save Draft</Button></Card>}</div><LinkedInPreview title={formData.title} content={postData.content} hashtags={postData.hashtags} cta={postData.cta} /></div>;
}
