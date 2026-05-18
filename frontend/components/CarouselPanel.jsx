'use client';
import { useState } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Input from '@/components/Input';
import Textarea from '@/components/Textarea';
import { callAI } from '@/lib/modelResolver';
import { parseJSON } from '@/lib/api';

const SLIDE_THEMES = [
  { bg: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', accent: '#a78bfa', dot: '#c4b5fd', label: 'HOOK' },
  { bg: 'linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)', accent: '#93c5fd', dot: '#bae6fd', label: 'INSIGHT' },
  { bg: 'linear-gradient(135deg, #10b981 0%, #0ea5e9 100%)', accent: '#6ee7b7', dot: '#a7f3d0', label: 'DETAIL' },
  { bg: 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)', accent: '#fcd34d', dot: '#fde68a', label: 'EXAMPLE' },
  { bg: 'linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)', accent: '#c4b5fd', dot: '#f9a8d4', label: 'KEY POINT' },
  { bg: 'linear-gradient(135deg, #14b8a6 0%, #6366f1 100%)', accent: '#99f6e4', dot: '#a5f3fc', label: 'TAKEAWAY' },
  { bg: 'linear-gradient(135deg, #f97316 0%, #db2777 100%)', accent: '#fed7aa', dot: '#fbcfe8', label: 'ACTION' },
  { bg: 'linear-gradient(135deg, #1d4ed8 0%, #0891b2 100%)', accent: '#93c5fd', dot: '#a5f3fc', label: 'CTA' },
];

function SlideDiagram({ index, bullets = [] }) {
  const theme = SLIDE_THEMES[index % SLIDE_THEMES.length];
  const count = Math.min(bullets.length || 3, 5);

  if (index === 0) {
    return (
      <svg width="120" height="80" viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-30 absolute bottom-4 right-4">
        <circle cx="60" cy="40" r="35" stroke="white" strokeWidth="2" strokeDasharray="6 4"/>
        <circle cx="60" cy="40" r="22" fill="white" fillOpacity="0.15"/>
        <circle cx="60" cy="40" r="8" fill="white" fillOpacity="0.4"/>
        <line x1="60" y1="5" x2="60" y2="75" stroke="white" strokeWidth="1" strokeOpacity="0.4"/>
        <line x1="25" y1="40" x2="95" y2="40" stroke="white" strokeWidth="1" strokeOpacity="0.4"/>
      </svg>
    );
  }

  if (bullets.length >= 3) {
    const barW = 12;
    const gap = 8;
    const heights = bullets.slice(0, Math.min(count, 5)).map((_, i) => 20 + ((i * 17) % 40));
    const totalW = count * (barW + gap) - gap;
    const startX = (120 - totalW) / 2;
    return (
      <svg width="120" height="80" viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-25 absolute bottom-4 right-4">
        {heights.map((h, i) => (
          <rect key={i} x={startX + i * (barW + gap)} y={70 - h} width={barW} height={h} rx="3" fill="white"/>
        ))}
        <line x1="10" y1="70" x2="110" y2="70" stroke="white" strokeWidth="1.5" strokeOpacity="0.6"/>
      </svg>
    );
  }

  return (
    <svg width="120" height="80" viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-25 absolute bottom-4 right-4">
      <rect x="15" y="10" width="38" height="24" rx="4" fill="white" fillOpacity="0.3"/>
      <rect x="67" y="10" width="38" height="24" rx="4" fill="white" fillOpacity="0.3"/>
      <rect x="41" y="46" width="38" height="24" rx="4" fill="white" fillOpacity="0.3"/>
      <line x1="34" y1="22" x2="67" y2="22" stroke="white" strokeWidth="1.5" strokeOpacity="0.5"/>
      <line x1="60" y1="34" x2="60" y2="46" stroke="white" strokeWidth="1.5" strokeOpacity="0.5"/>
    </svg>
  );
}

export default function CarouselPanel({ onAttach }) {
  const [topic, setTopic] = useState('');
  const [slides, setSlides] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeSlide, setActiveSlide] = useState(0);

  const generate = async () => {
    if (!topic.trim()) {
      setError('Please enter a topic');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const systemMsg = 'You are a LinkedIn carousel content expert. Create engaging multi-slide carousel content.';
      const userMsg = `Create a LinkedIn carousel about "${topic}".

Return ONLY valid JSON (no markdown):
{
  "title": "carousel title",
  "slides": [
    {"slide_num": 1, "heading": "slide title", "body": "2-3 sentences of content", "bullets": ["point 1", "point 2", "point 3"]},
    ...
  ],
  "closing_cta": "call to action text"
}

Rules:
- 5-8 slides
- Slide 1 is a hook/title slide
- Last slide is CTA
- Each slide should be self-contained but flow as a story
- Use concrete examples and data points
- Professional but engaging tone`;

      const response = await callAI('suggestions', userMsg, systemMsg);
      const parsed = parseJSON(response);
      setSlides(parsed.slides || []);
      setActiveSlide(0);
    } catch (e) {
      setError(e.message || 'Failed to generate carousel');
    } finally {
      setLoading(false);
    }
  };

  const updateSlide = (index, field, value) => {
    setSlides(prev => prev.map((s, i) =>
      i === index ? { ...s, [field]: value } : s
    ));
  };

  const addSlide = () => {
    setSlides(prev => [...prev, {
      slide_num: prev.length + 1,
      heading: 'New Slide',
      body: '',
      bullets: [''],
    }]);
    setActiveSlide(slides.length);
  };

  const removeSlide = (index) => {
    setSlides(prev => prev.filter((_, i) => i !== index).map((s, i) => ({ ...s, slide_num: i + 1 })));
    if (activeSlide >= slides.length - 1) setActiveSlide(Math.max(0, slides.length - 2));
  };

  return (
    <div className="space-y-4">
      <Card title="Carousel Generator" subtitle="Create multi-slide LinkedIn carousel content">
        <div className="space-y-4">
          <Input
            label="Carousel Topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., 5 AI trends every leader should know"
          />
          <Button onClick={generate} disabled={loading || !topic.trim()} variant="primary" loading={loading} className="w-full">
            {loading ? 'Generating...' : 'Generate Carousel'}
          </Button>
          {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>}
        </div>
      </Card>

      {slides.length > 0 && (
        <>
          {/* Slide thumbnail strip */}
          <div className="flex items-center gap-2 py-2 overflow-x-auto pb-1">
            {slides.map((s, i) => (
              <button
                key={i}
                onClick={() => setActiveSlide(i)}
                className="flex-shrink-0 rounded-lg text-white text-[10px] font-bold px-3 py-1.5 transition-all shadow-sm"
                style={{
                  background: SLIDE_THEMES[i % SLIDE_THEMES.length].bg,
                  opacity: i === activeSlide ? 1 : 0.5,
                  transform: i === activeSlide ? 'scale(1.08)' : 'scale(1)',
                  minWidth: '56px',
                }}
              >
                {i + 1}
              </button>
            ))}
            <button
              onClick={addSlide}
              className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-500 text-lg flex items-center justify-center ml-1 transition-colors"
            >
              +
            </button>
          </div>

          {/* Active slide preview */}
          <Card>
            <div
              className="rounded-xl text-white min-h-[320px] flex flex-col justify-between relative overflow-hidden"
              style={{ background: SLIDE_THEMES[activeSlide % SLIDE_THEMES.length].bg, padding: '2rem' }}
            >
              {/* Decorative background circles */}
              <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-white/5 pointer-events-none" />
              <div className="absolute -bottom-16 -left-8 w-48 h-48 rounded-full bg-white/5 pointer-events-none" />

              {/* SVG diagram */}
              <SlideDiagram index={activeSlide} bullets={slides[activeSlide]?.bullets} />

              <div className="relative z-10">
                {/* Slide type label + progress pills */}
                <div className="flex items-center gap-2 mb-4">
                  <span
                    className="text-[10px] font-bold tracking-widest px-2.5 py-1 rounded-full"
                    style={{ background: 'rgba(255,255,255,0.2)', color: 'white', letterSpacing: '0.12em' }}
                  >
                    {SLIDE_THEMES[activeSlide % SLIDE_THEMES.length].label}
                  </span>
                  <div className="flex gap-1 ml-auto">
                    {slides.map((_, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveSlide(i)}
                        className="transition-all rounded-full"
                        style={{
                          width: i === activeSlide ? '20px' : '6px',
                          height: '6px',
                          background: i === activeSlide ? 'white' : 'rgba(255,255,255,0.35)',
                        }}
                      />
                    ))}
                  </div>
                </div>

                <h3 className="text-2xl font-bold mb-3 leading-tight">{slides[activeSlide]?.heading}</h3>

                {slides[activeSlide]?.body && (
                  <p className="text-sm leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.88)' }}>
                    {slides[activeSlide].body}
                  </p>
                )}

                {slides[activeSlide]?.bullets?.length > 0 && (
                  <ul className="space-y-2">
                    {slides[activeSlide].bullets.filter(Boolean).map((b, j) => (
                      <li key={j} className="flex items-start gap-2.5 text-sm">
                        <span
                          className="mt-0.5 flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold"
                          style={{ background: 'rgba(255,255,255,0.25)' }}
                        >
                          {j + 1}
                        </span>
                        <span style={{ color: 'rgba(255,255,255,0.92)' }}>{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Bottom nav */}
              <div className="relative z-10 flex justify-between items-center mt-6 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                <button
                  onClick={() => setActiveSlide(Math.max(0, activeSlide - 1))}
                  disabled={activeSlide === 0}
                  className="flex items-center gap-1.5 text-sm font-medium transition-opacity disabled:opacity-30"
                  style={{ color: 'rgba(255,255,255,0.85)' }}
                >
                  &#8592; Prev
                </button>
                <span className="text-xs font-semibold tabular-nums" style={{ color: 'rgba(255,255,255,0.6)' }}>
                  {activeSlide + 1} / {slides.length}
                </span>
                <button
                  onClick={() => setActiveSlide(Math.min(slides.length - 1, activeSlide + 1))}
                  disabled={activeSlide === slides.length - 1}
                  className="flex items-center gap-1.5 text-sm font-medium transition-opacity disabled:opacity-30"
                  style={{ color: 'rgba(255,255,255,0.85)' }}
                >
                  Next &#8594;
                </button>
              </div>
            </div>
          </Card>

          {/* Slide editor */}
          <Card title={`Edit Slide ${activeSlide + 1}`}>
            <div className="space-y-3">
              <Input
                label="Heading"
                value={slides[activeSlide]?.heading || ''}
                onChange={(e) => updateSlide(activeSlide, 'heading', e.target.value)}
              />
              <Textarea
                label="Body"
                value={slides[activeSlide]?.body || ''}
                onChange={(e) => updateSlide(activeSlide, 'body', e.target.value)}
                rows={3}
              />
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Bullet Points</label>
                {(slides[activeSlide]?.bullets || []).map((b, j) => (
                  <input
                    key={j}
                    type="text"
                    value={b}
                    onChange={(e) => {
                      const newBullets = [...(slides[activeSlide]?.bullets || [])];
                      newBullets[j] = e.target.value;
                      updateSlide(activeSlide, 'bullets', newBullets);
                    }}
                    className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm mb-1 focus:ring-2 focus:ring-linkedin-500 focus:border-linkedin-500"
                    placeholder={`Point ${j + 1}`}
                  />
                ))}
              </div>
              <div className="flex gap-2">
                <Button onClick={() => removeSlide(activeSlide)} variant="danger" size="sm" disabled={slides.length <= 1}>
                  Remove Slide
                </Button>
              </div>
            </div>
          </Card>

          {onAttach && (
            <Button onClick={() => onAttach(slides)} variant="primary" className="w-full">
              Attach Carousel to Post
            </Button>
          )}
        </>
      )}
    </div>
  );
}
