export const formatDate = (v) => (v ? new Date(v).toLocaleDateString() : '');
export const countCharacters = (s='') => s.length;
export const parseHashtags = (s='') => s.split(' ').filter(Boolean);
