'use client';
import { useEffect, useState } from 'react';
import { IconLinkedIn, IconSparkles, IconCheck, IconX, IconExternalLink } from '@/components/icons';
import { callAI } from '@/lib/modelResolver';
import { publishDirect, checkLinkedInAuth, getLinkedInAuthUrl } from '@/lib/linkedin';
import { currentDateLabel } from '@/lib/utils';

const TONES = [
  { id: 'professional', label: 'Professional' },
  { id: 'warm', label: 'Warm' },
  { id: 'celebratory', label: 'Celebratory' },
  { id: 'concise', label: 'Concise' },
];

export default function PublishComposerModal({ open, onClose, initialContent = '', title = '', source = '', onPublished }) {
  const [content, setContent] = useState(initialContent);
  const [tone, setTone] = useState('professional');
  const [rewriting, setRewriting] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [published, setPublished] = useState(null);
  const [error, setError] = useState('');
  const auth = checkLinkedInAuth();

  useEffect(() => {
    if (open) {
      setContent(initialContent);
      setPublished(null);
      setError('');
      setPublishing(false);
    }
  }, [open, initialContent]);

  useEffect(() => {
    if (!open) return;
    const handleEsc = (e) => { if (e.key === 'Escape' && !publishing) onClose(); };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [open, onClose, publishing]);

  const handleRewrite = async () => {
    if (!content.trim()) return;
    setRewriting(true);
    try {
      const systemMsg = `You are a LinkedIn content editor. Today is ${currentDateLabel()}. Rewrite the following in a ${tone} tone. Return ONLY the rewritten text, no explanation.`;
      const response = await callAI('suggestions', content, systemMsg);
      setContent(response);
    } catch (e) {
      setError(`Rewrite failed: ${e.message}`);
    } finally {
      setRewriting(false);
    }
  };

  const handlePublish = async () => {
    if (!content.trim()) return;
    setPublishing(true);
    setError('');
    try {
      const result = await publishDirect(content, source);
      setPublished(result);
      if (onPublished) onPublished(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setPublishing(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in" onClick={(e) => { if (e.target === e.currentTarget && !publishing) onClose(); }}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-xl mx-4 animate-scale-in flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <IconLinkedIn size={20} className="text-linkedin-600" />
            <h2 className="text-lg font-semibold text-gray-900">Post to LinkedIn</h2>
          </div>
          <button onClick={onClose} disabled={publishing} className="p-1.5 rounded-lg hover:bg-gray-100 transition text-gray-400 hover:text-gray-600 disabled:opacity-50">
            <IconX size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {published ? (
            <div className="text-center py-6 space-y-3">
              <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto">
                <IconCheck size={28} className="text-green-600" />
              </div>
              <h3 className="font-semibold text-gray-900 text-lg">Published to LinkedIn!</h3>
              {published.linkedin_url && (
                <a href={published.linkedin_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-sm text-linkedin-600 hover:text-linkedin-700 font-medium">
                  <IconExternalLink size={14} /> View on LinkedIn
                </a>
              )}
              <button onClick={onClose} className="block mx-auto mt-4 btn-primary !px-8">Done</button>
            </div>
          ) : (
            <>
              {title && <div className="text-sm font-medium text-gray-500">{title}</div>}

              <div className="flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${auth.connected ? 'bg-green-500' : 'bg-red-400'}`} />
                <span className="text-xs text-gray-500">
                  {auth.connected ? `Connected as ${auth.name}` : 'Not connected'}
                </span>
                {!auth.connected && (
                  <a href={getLinkedInAuthUrl()} className="text-xs text-linkedin-600 hover:text-linkedin-700 font-medium ml-1">Connect LinkedIn</a>
                )}
              </div>

              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={8}
                className="input-field !text-sm resize-none"
                placeholder="Write your LinkedIn post..."
              />

              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">{content.length} characters</span>
                {content.length > 3000 && <span className="text-xs text-red-500">LinkedIn limit: 3,000 characters</span>}
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-gray-600">Tone</label>
                <div className="flex flex-wrap gap-2">
                  {TONES.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setTone(t.id)}
                      className={`px-3 py-1.5 text-xs rounded-lg border transition font-medium ${
                        tone === t.id
                          ? 'bg-studio-50 border-studio-200 text-studio-700'
                          : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                  <button
                    onClick={handleRewrite}
                    disabled={rewriting || !content.trim()}
                    className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 transition font-medium disabled:opacity-50"
                  >
                    <IconSparkles size={12} />
                    {rewriting ? 'Rewriting...' : 'AI Rewrite'}
                  </button>
                </div>
              </div>

              <div className="bg-gray-50 border border-gray-100 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-studio-100 to-linkedin-100 flex items-center justify-center text-xs font-bold text-studio-700">
                    {auth.name ? auth.name.charAt(0).toUpperCase() : 'U'}
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-gray-900">{auth.name || 'Your Name'}</div>
                    <div className="text-xs text-gray-400">Just now</div>
                  </div>
                </div>
                <div className="text-xs text-gray-700 whitespace-pre-wrap line-clamp-6">{content || 'Your post preview will appear here...'}</div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>
              )}
            </>
          )}
        </div>

        {!published && (
          <div className="flex items-center justify-end gap-3 p-5 border-t border-gray-100">
            <button onClick={onClose} disabled={publishing} className="btn-secondary !py-2">Cancel</button>
            <button
              onClick={handlePublish}
              disabled={publishing || !content.trim() || !auth.connected}
              className="inline-flex items-center gap-2 px-5 py-2 bg-linkedin-600 text-white rounded-xl text-sm font-semibold shadow-sm hover:bg-linkedin-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <IconLinkedIn size={15} />
              {publishing ? 'Publishing...' : 'Post Now'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
