'use client';
import { useState } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Input from '@/components/Input';
import Textarea from '@/components/Textarea';
import Select from '@/components/Select';
import { callAI } from '@/lib/modelResolver';
import { parseJSON } from '@/lib/api';

const NEWSLETTER_TONES = [
  { value: 'professional', label: 'Professional' },
  { value: 'educational', label: 'Educational' },
  { value: 'thought-leader', label: 'Thought Leadership' },
  { value: 'conversational', label: 'Conversational' },
];

export default function NewsletterPanel({ onAttach }) {
  const [topic, setTopic] = useState('');
  const [tone, setTone] = useState('professional');
  const [title, setTitle] = useState('');
  const [subtitle, setSubtitle] = useState('');
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    if (!topic.trim()) {
      setError('Please enter a topic');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const systemMsg = 'You are a LinkedIn newsletter writer. Create structured, long-form articles.';
      const userMsg = `Write a LinkedIn newsletter article about "${topic}" in a ${tone} tone.

Return ONLY valid JSON (no markdown):
{
  "title": "newsletter title",
  "subtitle": "one-line subtitle",
  "sections": [
    {"heading": "section heading", "content": "2-4 paragraphs of well-written content"},
    ...
  ],
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
  "cta": "closing call to action"
}

Rules:
- 4-6 sections
- Professional but readable tone
- Include data points and examples where relevant
- Total word count: 800-1500 words
- Each section should build on the previous one`;

      const response = await callAI('post_generation', userMsg, systemMsg);
      const parsed = parseJSON(response);
      setTitle(parsed.title || '');
      setSubtitle(parsed.subtitle || '');
      setSections(parsed.sections || []);
    } catch (e) {
      setError(e.message || 'Failed to generate newsletter');
    } finally {
      setLoading(false);
    }
  };

  const updateSection = (index, field, value) => {
    setSections(prev => prev.map((s, i) =>
      i === index ? { ...s, [field]: value } : s
    ));
  };

  const totalWords = sections.reduce((sum, s) => sum + (s.content || '').split(/\s+/).length, 0);

  return (
    <div className="space-y-4">
      <Card title="Newsletter Article" subtitle="Create long-form LinkedIn newsletter content">
        <div className="space-y-4">
          <Input
            label="Newsletter Topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., The future of AI agents in enterprise"
          />
          <Select label="Tone" value={tone} onChange={(e) => setTone(e.target.value)} options={NEWSLETTER_TONES} />
          <Button onClick={generate} disabled={loading || !topic.trim()} variant="primary" loading={loading} className="w-full">
            {loading ? 'Generating...' : 'Generate Newsletter'}
          </Button>
          {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>}
        </div>
      </Card>

      {title && (
        <>
          {/* Header */}
          <Card>
            <Input
              label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Input
              label="Subtitle"
              value={subtitle}
              onChange={(e) => setSubtitle(e.target.value)}
              className="mt-3"
            />
            <div className="text-xs text-gray-500 mt-2">{totalWords} words</div>
          </Card>

          {/* Sections */}
          {sections.map((section, i) => (
            <Card key={i} title={`Section ${i + 1}`}>
              <Input
                label="Heading"
                value={section.heading}
                onChange={(e) => updateSection(i, 'heading', e.target.value)}
              />
              <Textarea
                label="Content"
                value={section.content}
                onChange={(e) => updateSection(i, 'content', e.target.value)}
                rows={6}
                className="mt-3"
              />
            </Card>
          ))}

          {/* Preview */}
          <Card title="Article Preview">
            <div className="prose prose-sm max-w-none">
              <h2 className="text-xl font-bold text-gray-900">{title}</h2>
              {subtitle && <p className="text-gray-500 italic">{subtitle}</p>}
              <hr className="my-4" />
              {sections.map((s, i) => (
                <div key={i} className="mb-6">
                  <h3 className="text-lg font-semibold text-gray-800">{s.heading}</h3>
                  <div className="text-sm text-gray-700 whitespace-pre-wrap mt-2">{s.content}</div>
                </div>
              ))}
            </div>
          </Card>

          {/* LinkedIn newsletter link */}
          <a
            href="https://www.linkedin.com/article/newsletter/new/"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-3 bg-gradient-to-r from-linkedin-600 to-linkedin-500 text-white rounded-xl p-4 shadow-md hover:shadow-lg transition-shadow no-underline"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="white"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
            <div>
              <div className="font-bold text-sm">Publish as LinkedIn Newsletter</div>
              <div className="text-xs opacity-85">Copy your content and publish directly on LinkedIn</div>
            </div>
          </a>

          {onAttach && (
            <Button onClick={() => onAttach({ title, subtitle, sections })} variant="primary" className="w-full">
              Save Newsletter Draft
            </Button>
          )}
        </>
      )}
    </div>
  );
}
