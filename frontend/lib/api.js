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
      content_type: data.content_type || 'text',
      media: data.media || null,
      carousel_slides: data.carousel_slides || null,
    }),
  });

export const publishPost = (postId) => {
  let accessToken = '';
  let authorUrn = '';
  if (typeof window !== 'undefined') {
    try {
      const oauth = JSON.parse(localStorage.getItem('linkedin_oauth') || '{}');
      accessToken = oauth.access_token || '';
      authorUrn = oauth.author_urn || '';
    } catch {}
  }
  return req('/api/posts/publish', {
    method: 'POST',
    body: JSON.stringify({
      post_id: postId,
      access_token: accessToken,
      author_urn: authorUrn,
    }),
  });
};

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
export const searchSerp = (q, key, freshness = '7d') => req(`/api/serp/search?q=${encodeURIComponent(q)}&key=${key || ''}&freshness=${freshness}`);
export const scrapeProfile = (url, key) => req(`/api/serp/profile/scrape?linkedin_url=${encodeURIComponent(url)}&key=${key || ''}`);
export const getConnections = (params = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') qs.set(k, String(v)); });
  return req(`/api/serp/connections?${qs.toString()}`);
};
export const searchPeople = (params = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') qs.set(k, String(v)); });
  return req(`/api/serp/people?${qs.toString()}`);
};

// My Network / Connections (real LinkedIn My Network support + simulated fallback)
export const getMyConnections = (params = {}) =>
  req(`/api/serp/connections?${new URLSearchParams(params).toString()}`);

export const getLinkedinStatus = () => req('/api/serp/linkedin/status').catch(() => ({
  linkedinOAuthConfigured: false,
  linkedinSessionConfigured: false,
  serpConfigured: false,
  csvImported: false,
  activeSource: 'none',
  profileHandle: ''
}));
export const connectLinkedinSession = (liAt) =>
  req('/api/serp/linkedin/session', {
    method: 'POST',
    body: JSON.stringify({ li_at: liAt || '' }),
  });

export const getMyNetworkContext = () =>
  req('/api/serp/connections?mode=context').catch(() => ({
    simulated: true,
    message: 'Real LinkedIn API/session unavailable. Using search simulation. Open official pages for full access.',
    my_network_url: 'https://www.linkedin.com/mynetwork/',
    notifications_url: 'https://www.linkedin.com/notifications/?filter=all',
  }));

export const openMyNetwork = () => {
  if (typeof window !== 'undefined') {
    window.open('https://www.linkedin.com/mynetwork/', '_blank');
  }
};

export const openNotifications = () => {
  if (typeof window !== 'undefined') {
    window.open('https://www.linkedin.com/notifications/?filter=all', '_blank');
  }
};
export const uploadConnectionsCsv = async (file, page = 1, perPage = 10) => {
  const form = new FormData();
  form.append('file', file);
  const qs = `page=${page}&per_page=${perPage}`;
  const res = await fetch(`${API_URL}/api/serp/connections/import-csv?${qs}`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`CSV upload failed: ${res.status}`);
  return res.json();
};

// Discovery Reports
export const getDiscoveryReports = () => req('/api/discovery-reports');
export const getDiscoveryReport = (provider) => req(`/api/discovery-reports/${provider}`);
export const getDiscoveryImageUrl = (provider, filename) => `/api/proxy/api/discovery-reports/${provider}/image/${filename}`;
export const publishDiscoveryToLinkedIn = (provider, includeImage = true) =>
  req(`/api/discovery-reports/${provider}/publish/linkedin`, {
    method: 'POST',
    body: JSON.stringify({ include_image: includeImage }),
  });
export const publishDiscoveryToDevTo = (provider, tags = [], published = true) =>
  req(`/api/discovery-reports/${provider}/publish/devto`, {
    method: 'POST',
    body: JSON.stringify({ tags, published }),
  });

// JSON parse helper
export const parseJSON = (text) => {
  const clean = text.replace(/```json|```/g, "").trim();
  return JSON.parse(clean);
};

// ── Content plan ────────────────────────────────────────────────────────────

export const generateContentPlan = (options) =>
  req('/api/generate/content-plan', {
    method: 'POST',
    body: JSON.stringify(options),
  });

export const getProviders = () =>
  req('/api/generate/providers');

// ── Media generation ────────────────────────────────────────────────────────

export const generateImage = (options) =>
  req('/api/media/images/generate', {
    method: 'POST',
    body: JSON.stringify(options),
  });

export const generateVideoScript = (options) =>
  req('/api/media/video/script', {
    method: 'POST',
    body: JSON.stringify(options),
  });

export const startVideoGeneration = (options) =>
  req('/api/media/video/generate', {
    method: 'POST',
    body: JSON.stringify(options),
  });

export const getMediaJobStatus = (jobId) =>
  req(`/api/media/job/${jobId}`);

export const getMediaFileUrl = (filename) =>
  `/api/proxy/api/media/file/${filename}`;

export const getMediaStyles = () =>
  req('/api/media/styles');

// ── Trend discovery ─────────────────────────────────────────────────────────

export const discoverTrends = (options) =>
  req('/api/trends/discover', {
    method: 'POST',
    body: JSON.stringify(options),
  });

export const searchWithFreshness = (options) =>
  req('/api/trends/search', {
    method: 'POST',
    body: JSON.stringify(options),
  });
