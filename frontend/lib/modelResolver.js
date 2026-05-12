import { API_URL } from '@/lib/constants';

export const USE_CASES = {
  feed: 'feed',
  digest: 'digest',
  suggestions: 'suggestions',
  ideas: 'ideas',
  images: 'images',
  video: 'video',
  post_generation: 'post_generation',
};

export const getModel = (useCase) => {
  try {
    const assignments = JSON.parse(localStorage.getItem('model_assignments') || '{}');
    if (assignments[useCase]) return assignments[useCase];
  } catch {}
  const defaults = {
    feed: 'models/gemini-2.5-flash',
    digest: 'models/gemini-2.5-flash',
    suggestions: 'models/gemini-2.5-flash',
    ideas: 'models/gemini-2.5-flash',
    images: 'models/gemini-2.5-flash',
    video: 'models/gemini-2.5-flash',
    post_generation: 'models/gemini-2.5-flash',
  };
  return defaults[useCase] || 'models/gemini-2.5-flash';
};

const detectProvider = (modelId) => {
  if (modelId.startsWith('models/')) return 'google';
  if (modelId.startsWith('claude-')) return 'anthropic';
  return 'openai';
};

export const callAI = async (useCase, userPrompt, systemPrompt = '') => {
  const modelId = getModel(useCase);
  const provider = detectProvider(modelId);

  const apiPost = async (path, payload) => {
    const opts = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    };
    try {
      const res = await fetch(`${API_URL}${path}`, opts);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      return await res.json();
    } catch (e) {
      try {
        const res = await fetch(`/api/proxy${path}`, opts);
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || `HTTP ${res.status}`);
        }
        return await res.json();
      } catch (proxyErr) {
        throw e;
      }
    }
  };

  // All providers go through the backend for consistency
  const data = await apiPost('/api/ai/generate', {
    model: modelId,
    prompt: userPrompt,
    system: systemPrompt,
  });

  return data.text || data.content || '';
};
