'use client';
import { useState } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Input from '@/components/Input';
import Textarea from '@/components/Textarea';
import Select from '@/components/Select';
import { callAI } from '@/lib/modelResolver';
import { parseJSON } from '@/lib/api';

const POLL_DURATIONS = [
  { value: '1', label: '1 Day' },
  { value: '3', label: '3 Days' },
  { value: '7', label: '7 Days' },
  { value: '14', label: '14 Days' },
];

export default function PollPanel({ onAttach }) {
  const [topic, setTopic] = useState('');
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState(['', '', '', '']);
  const [duration, setDuration] = useState('7');
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const generate = async () => {
    if (!topic.trim()) {
      setError('Please enter a poll topic');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const systemMsg = 'You are a LinkedIn engagement expert. Create polls that drive discussion.';
      const userMsg = `Create a LinkedIn poll about "${topic}".

Return ONLY valid JSON (no markdown):
{
  "question": "the poll question (max 140 chars)",
  "options": ["option 1", "option 2", "option 3", "option 4"],
  "context_post": "2-3 sentence post text to accompany the poll, explaining why this matters"
}

Rules:
- Question should be thought-provoking
- Options should be clearly distinct
- 4 options exactly
- Context post should drive engagement`;

      const response = await callAI('suggestions', userMsg, systemMsg);
      const parsed = parseJSON(response);
      setQuestion(parsed.question || '');
      setOptions(parsed.options || ['', '', '', '']);
      setContext(parsed.context_post || '');
    } catch (e) {
      setError(e.message || 'Failed to generate poll');
    } finally {
      setLoading(false);
    }
  };

  const updateOption = (index, value) => {
    setOptions(prev => prev.map((o, i) => i === index ? value : o));
  };

  return (
    <div className="space-y-4">
      <Card title="Poll Creator" subtitle="Create engaging LinkedIn polls">
        <div className="space-y-4">
          <Input
            label="Poll Topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., Best AI framework for production"
          />
          <Button onClick={generate} disabled={loading || !topic.trim()} variant="primary" loading={loading} className="w-full">
            {loading ? 'Generating...' : 'Generate Poll'}
          </Button>
          {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>}
        </div>
      </Card>

      {question && (
        <>
          <Card title="Poll Question">
            <div className="space-y-4">
              <Textarea
                label="Question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={2}
              />
              <div className="space-y-2">
                {options.map((opt, i) => (
                  <Input
                    key={i}
                    label={`Option ${i + 1}`}
                    value={opt}
                    onChange={(e) => updateOption(i, e.target.value)}
                    placeholder={`Option ${i + 1}`}
                  />
                ))}
              </div>
              <Select label="Poll Duration" value={duration} onChange={(e) => setDuration(e.target.value)} options={POLL_DURATIONS} />
              <Textarea
                label="Context Post (accompanies the poll)"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                rows={3}
              />
            </div>
          </Card>

          {/* Poll Preview */}
          <Card title="Poll Preview">
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              {context && <p className="text-sm text-gray-800 mb-4">{context}</p>}
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <div className="p-4 bg-gray-50">
                  <p className="font-semibold text-sm text-gray-900">{question}</p>
                </div>
                <div className="p-3 space-y-2">
                  {options.filter(Boolean).map((opt, i) => (
                    <div key={i} className="relative bg-linkedin-50 border border-linkedin-200 rounded-lg px-4 py-2.5 text-sm text-gray-800 cursor-pointer hover:bg-linkedin-100 transition">
                      {opt}
                    </div>
                  ))}
                </div>
                <div className="px-4 py-2 text-xs text-gray-500 border-t border-gray-100">
                  {duration} day{duration !== '1' ? 's' : ''} remaining
                </div>
              </div>
            </div>
          </Card>

          {onAttach && (
            <Button onClick={() => onAttach({ question, options: options.filter(Boolean), duration, context })} variant="primary" className="w-full">
              Attach Poll to Post
            </Button>
          )}
        </>
      )}
    </div>
  );
}
