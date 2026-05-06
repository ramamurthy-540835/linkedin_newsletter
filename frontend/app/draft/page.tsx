'use client';

import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export default function DraftPage() {
  const [topic, setTopic] = useState('AI workflows for B2B teams');
  const [audience, setAudience] = useState('founders and operators');
  const [output, setOutput] = useState('');

  const generate = async () => {
    const res = await fetch(`${API}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, audience, tone: 'professional', objective: 'engagement' })
    });
    const data = await res.json();
    setOutput(`${data.post_text}\n\n${data.hashtags.join(' ')}`);
  };

  return (
    <main className="container">
      <h1>Draft Composer</h1>
      <div className="card">
        <label>Topic</label>
        <input value={topic} onChange={(e) => setTopic(e.target.value)} />
        <label>Audience</label>
        <input value={audience} onChange={(e) => setAudience(e.target.value)} />
        <button onClick={generate}>Generate Post</button>
        <label>Preview</label>
        <textarea rows={14} value={output} onChange={(e) => setOutput(e.target.value)} />
      </div>
    </main>
  );
}
