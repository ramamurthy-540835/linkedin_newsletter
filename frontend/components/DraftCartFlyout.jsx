'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { IconX, IconCopy, IconCheck, IconEdit, IconTrash, IconQueue, IconLibrary, IconCalendar } from '@/components/icons';
import { savePost } from '@/lib/api';

const TYPE_BADGES = {
  post: { label: 'Post', bg: 'bg-blue-50', text: 'text-blue-700' },
  comment: { label: 'Comment', bg: 'bg-green-50', text: 'text-green-700' },
  repost: { label: 'Repost', bg: 'bg-purple-50', text: 'text-purple-700' },
  message: { label: 'Message', bg: 'bg-pink-50', text: 'text-pink-700' },
  carousel: { label: 'Ideas', bg: 'bg-amber-50', text: 'text-amber-700' },
  image: { label: 'Image', bg: 'bg-indigo-50', text: 'text-indigo-700' },
};

function timeAgo(ts) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function DraftCartFlyout({ open, onClose, items, onRemove, onToast }) {
  const router = useRouter();
  const [copiedId, setCopiedId] = useState(null);
  const [savingId, setSavingId] = useState(null);

  useEffect(() => {
    if (!open) return;
    const handleEsc = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [open, onClose]);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  const handleCopy = (item) => {
    navigator.clipboard.writeText(item.content);
    setCopiedId(item.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleEdit = (item) => {
    localStorage.setItem('prefill_topic', item.title || '');
    localStorage.setItem('prefill_hook', item.content || '');
    onClose();
    router.push('/create');
  };

  const handleSaveToLibrary = async (item) => {
    setSavingId(item.id);
    try {
      await savePost({
        title: item.title,
        content: item.content,
        content_type: item.type === 'message' ? 'text' : item.type,
        topic: item.title,
      });
      onRemove(item.id);
      if (onToast) onToast('Saved to Content Library');
    } catch (e) {
      if (onToast) onToast(`Save failed: ${e.message}`);
    } finally {
      setSavingId(null);
    }
  };

  const handleSchedule = (item) => {
    localStorage.setItem('prefill_topic', item.title || '');
    localStorage.setItem('prefill_hook', item.content || '');
    onClose();
    router.push('/create?schedule=true');
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="absolute top-0 right-0 h-full w-[420px] max-w-full bg-white shadow-elevated flex flex-col animate-slide-in-right">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <IconQueue size={20} className="text-studio-600" />
            <h2 className="font-bold text-gray-900">Draft Cart</h2>
            {items.length > 0 && (
              <span className="text-xs bg-studio-100 text-studio-700 px-2 py-0.5 rounded-full font-medium">{items.length}</span>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <IconX size={18} className="text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full p-8 text-center">
              <IconQueue size={48} className="text-gray-200 mb-4" />
              <p className="text-sm font-medium text-gray-500">No drafts yet</p>
              <p className="text-xs text-gray-400 mt-1">Generate from Feed, Ideas, or Network Moments.</p>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {items.map((item) => {
                const badge = TYPE_BADGES[item.type] || TYPE_BADGES.post;
                return (
                  <div key={item.id} className="p-4 bg-gray-50 border border-gray-100 rounded-xl hover:border-gray-200 transition">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.bg} ${badge.text}`}>{badge.label}</span>
                          {item.source && <span className="text-xs text-gray-400">{item.source}</span>}
                        </div>
                        <div className="font-semibold text-sm text-gray-900 line-clamp-1">{item.title}</div>
                        <div className="text-xs text-gray-600 mt-1 line-clamp-3 whitespace-pre-wrap">{item.content}</div>
                        <div className="text-xs text-gray-400 mt-1.5">{timeAgo(item.createdAt)}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 mt-3 pt-2.5 border-t border-gray-100">
                      <button onClick={() => handleEdit(item)} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-studio-600 hover:bg-studio-50 rounded-lg transition" title="Edit in Creator">
                        <IconEdit size={13} /> Edit
                      </button>
                      <button onClick={() => handleCopy(item)} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-studio-600 hover:bg-studio-50 rounded-lg transition" title="Copy to clipboard">
                        {copiedId === item.id ? <><IconCheck size={13} /> Copied!</> : <><IconCopy size={13} /> Copy</>}
                      </button>
                      <button onClick={() => handleSaveToLibrary(item)} disabled={savingId === item.id} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-green-600 hover:bg-green-50 rounded-lg transition disabled:opacity-50" title="Save to Content Library">
                        <IconLibrary size={13} /> {savingId === item.id ? 'Saving...' : 'Save'}
                      </button>
                      <button onClick={() => onRemove(item.id)} className="ml-auto flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition" title="Remove">
                        <IconTrash size={13} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
