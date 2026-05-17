'use client';
import { useState } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Input from '@/components/Input';
import Textarea from '@/components/Textarea';
import { callAI } from '@/lib/modelResolver';
import { parseJSON } from '@/lib/api';

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
          {/* Slide navigation dots */}
          <div className="flex items-center justify-center gap-2 py-2">
            {slides.map((_, i) => (
              <button
                key={i}
                onClick={() => setActiveSlide(i)}
                className={`w-3 h-3 rounded-full transition-all ${
                  i === activeSlide ? 'bg-linkedin-600 scale-125' : 'bg-gray-300 hover:bg-gray-400'
                }`}
              />
            ))}
            <button onClick={addSlide} className="w-6 h-6 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 text-xs flex items-center justify-center ml-2">
              +
            </button>
          </div>

          {/* Active slide preview */}
          <Card>
            <div className="bg-gradient-to-br from-linkedin-600 to-linkedin-700 rounded-xl p-8 text-white min-h-[300px] flex flex-col justify-between">
              <div>
                <div className="text-xs font-semibold opacity-70 mb-2">
                  Slide {activeSlide + 1} of {slides.length}
                </div>
                <h3 className="text-2xl font-bold mb-4">{slides[activeSlide]?.heading}</h3>
                {slides[activeSlide]?.body && (
                  <p className="text-sm opacity-90 mb-4">{slides[activeSlide].body}</p>
                )}
                {slides[activeSlide]?.bullets?.length > 0 && (
                  <ul className="space-y-2">
                    {slides[activeSlide].bullets.map((b, j) => (
                      <li key={j} className="flex items-start gap-2 text-sm">
                        <span className="text-linkedin-200 mt-0.5">&#10003;</span>
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="flex justify-between items-center mt-4">
                <button
                  onClick={() => setActiveSlide(Math.max(0, activeSlide - 1))}
                  disabled={activeSlide === 0}
                  className="text-white/60 hover:text-white disabled:opacity-30"
                >
                  &#8592; Prev
                </button>
                <button
                  onClick={() => setActiveSlide(Math.min(slides.length - 1, activeSlide + 1))}
                  disabled={activeSlide === slides.length - 1}
                  className="text-white/60 hover:text-white disabled:opacity-30"
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
