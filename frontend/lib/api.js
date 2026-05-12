import { API_URL } from './constants';

async function req(path, opts = {}) {
  const requestInit = {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  };

  let res;
  try {
    res = await fetch(`${API_URL}${path}`, requestInit);
  } catch (directErr) {
    // Fall back to Next.js proxy when direct backend URL is unreachable.
    res = await fetch(`/api/proxy${path}`, requestInit);
  }

  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = body?.detail ? ` - ${body.detail}` : '';
    } catch {}
    throw new Error(`Request failed: ${res.status}${detail}`);
  }
  return res.status === 204 ? null : res.json();
}

export const getPosts = () => req('/api/posts').catch(() => []);
export const getPublishedPosts = () => req('/api/published-posts').catch(() => []);
export const getDrafts = async () => (await getPosts()).filter((p) => p.status === 'draft');

export const generatePost = async (data) => {
  const payload = {
    topic: data.topic || '',
    audience: data.audience || 'all',
    tone: data.tone || 'professional',
  };
  const out = await req('/api/posts/generate', { method: 'POST', body: JSON.stringify(payload) });
  return {
    content: out.content || '',
    hashtags: out.hashtags || [],
    cta: out.cta || '',
  };
};

export const savePost = (data) =>
  req('/api/posts/save', {
    method: 'POST',
    body: JSON.stringify({
      title: data.title || data.topic || 'Untitled',
      topic: data.topic || '',
      audience: data.audience || 'all',
      tone: data.tone || 'professional',
      content: data.content || '',
      hashtags: data.hashtags || [],
      cta: data.cta || '',
    }),
  });

export const publishPost = (postId) =>
  req('/api/posts/publish', {
    method: 'POST',
    body: JSON.stringify({
      post_id: postId,
      access_token: '',
    }),
  });

export const deletePost = (postId) =>
  req(`/api/posts/${postId}`, {
    method: 'DELETE',
  });

export const getLinkedInAuth = () => req('/api/auth/linkedin/url').then(() => ({ authenticated: true })).catch(() => ({ authenticated: false }));
export const startLinkedInAuth = async () => {
  const out = await req('/api/auth/linkedin/url');
  if (out?.url) window.location.href = out.url;
};

export const getPlatformCredentials = () => req('/api/admin/platforms').catch(() => ({}));
export const configurePlatform = (platform, data) => req(`/api/admin/platforms/${platform}`, { method: 'POST', body: JSON.stringify(data) });
export const testPlatform = (platform) => req(`/api/admin/platforms/${platform}/validate`, { method: 'POST', body: JSON.stringify({}) });

// SerpAPI endpoints
export const searchSerp = (q, key) => req(`/api/serp/search?q=${encodeURIComponent(q)}&key=${key || ''}`);
export const scrapeProfile = (url, key) => req(`/api/serp/profile/scrape?linkedin_url=${encodeURIComponent(url)}&key=${key || ''}`);

// Claude API helper
// JSON parse helper
export const parseJSON = (text) => {
  const clean = text.replace(/```json|```/g, "").trim();
  return JSON.parse(clean);
};
