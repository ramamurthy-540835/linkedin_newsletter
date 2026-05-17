import { API_URL } from '@/lib/constants';

export function checkLinkedInAuth() {
  if (typeof window === 'undefined') return { connected: false, name: '', authorUrn: '' };
  try {
    const raw = localStorage.getItem('linkedin_oauth');
    if (!raw) return { connected: false, name: '', authorUrn: '' };
    const data = JSON.parse(raw);
    return {
      connected: !!data.access_token,
      name: data.name || '',
      authorUrn: data.author_urn || '',
      profileUrl: data.profile_url || '',
    };
  } catch {
    return { connected: false, name: '', authorUrn: '' };
  }
}

export async function publishDirect(text, source = '') {
  const opts = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, source }),
  };

  let res;
  try {
    res = await fetch(`${API_URL}/api/posts/publish/direct`, opts);
  } catch {
    res = await fetch('/api/proxy/api/posts/publish/direct', opts);
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Publish failed: ${res.status}`);
  }

  return res.json();
}

export function getLinkedInAuthUrl() {
  return `${window.location.protocol}//${window.location.hostname}:8007/api/auth/linkedin`;
}
