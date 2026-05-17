export const formatDate = (v) => (v ? new Date(v).toLocaleDateString() : '');
export const countCharacters = (s='') => s.length;
export const parseHashtags = (s='') => s.split(' ').filter(Boolean);

const _now = () => new Date();
export const currentDateLabel = () => _now().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
export const currentMonthYear = () => _now().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
export const currentYear = () => _now().getFullYear();
export const currentIsoDate = () => _now().toISOString().slice(0, 10);

const STALE_PATTERNS = [/\b202[0-4]\b/, /\b2025\b/, /essential tech stack in \d{4}/i, /future of document management/i];
export const isStale = (text) => STALE_PATTERNS.some((p) => p.test(text));
export const filterStaleSuggestions = (items) => items.filter((s) => {
  const combined = `${s.topic || ''} ${s.hook || ''} ${s.why_trending || ''}`;
  return !isStale(combined);
});
