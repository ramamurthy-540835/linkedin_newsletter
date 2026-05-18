'use client';
import { useState, useEffect } from 'react';
import Button from '@/components/Button';
import LinkedInPreview from '@/components/LinkedInPreview';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorBanner from '@/components/ErrorBanner';
import SuccessBanner from '@/components/SuccessBanner';
import { getDrafts, publishPost, deletePost } from '@/lib/api';
import { getMediaFileUrl } from '@/lib/api';
import {
  IconSend,
  IconFile,
  IconTrash,
  IconQueue,
  IconCheckCircle,
  IconCalendar,
  IconSparkles,
  IconImage,
  IconVideo,
  IconLayers,
  IconChevronLeft,
  IconChevronRight,
  IconCreate,
  IconPoll,
  IconNewspaper,
} from '@/components/icons';

export default function PublishQueuePage() {
  const [drafts, setDrafts] = useState([]);
  const [selectedDraft, setSelectedDraft] = useState(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [publishResult, setPublishResult] = useState(null);
  const [pendingDeleteId, setPendingDeleteId] = useState(null);
  const [carouselIdx, setCarouselIdx] = useState(0);

  useEffect(() => {
    fetchDrafts();
  }, []);

  const fetchDrafts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getDrafts();
      setDrafts(data);
      if (data.length > 0) {
        setSelectedDraft(data[0]);
      }
    } catch (err) {
      console.error('Failed to load drafts:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (draftId) => {
    try {
      setError(null);
      await deletePost(draftId);
      const updated = drafts.filter((d) => d.id !== draftId);
      setDrafts(updated);
      if (selectedDraft?.id === draftId) {
        setSelectedDraft(updated.length > 0 ? updated[0] : null);
      }
      setSuccess('Draft deleted');
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      setError(`Failed to delete: ${err.message}`);
    }
  };

  const handlePublish = async () => {
    if (!selectedDraft) {
      setError('Please select a draft');
      return;
    }

    try {
      setPublishing(true);
      setError(null);

      const result = await publishPost(selectedDraft.id);
      const isLocal = result.linkedin_post_id?.startsWith('local-');

      setPublishResult(result);
      setSuccess(isLocal
        ? 'Post saved locally (LinkedIn credentials not configured)'
        : 'Post published to LinkedIn!'
      );

      if (!isLocal && result.linkedin_url) {
        setTimeout(() => window.open(result.linkedin_url, '_blank'), 1000);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setPublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Publish Queue</h1>
          <p className="text-sm text-gray-500 mt-1">Review and publish your drafts to LinkedIn</p>
        </div>
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Publish Queue</h1>
        <p className="text-sm text-gray-500 mt-1">{drafts.length} draft{drafts.length !== 1 ? 's' : ''} ready to publish</p>
      </div>

      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}
      {success && <SuccessBanner message={success} onClose={() => setSuccess(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Draft list */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-2xl shadow-card border border-gray-100 overflow-hidden">
            <div className="bg-gradient-to-r from-studio-50 to-linkedin-50 border-b border-studio-100 p-4 flex items-center gap-2">
              <IconQueue size={18} className="text-studio-600" />
              <h2 className="font-semibold text-sm text-gray-900">Drafts</h2>
              <span className="ml-auto text-xs bg-studio-100 text-studio-700 px-2 py-0.5 rounded-full font-medium">{drafts.length}</span>
            </div>

            {drafts.length === 0 ? (
              <div className="text-center py-12 px-4">
                <IconFile size={40} className="mx-auto text-gray-200 mb-3" />
                <h3 className="text-sm font-semibold text-gray-900 mb-1">No drafts yet</h3>
                <p className="text-xs text-gray-500 mb-4">Create content to get started</p>
                <Button href="/create" variant="primary" size="sm">
                  <IconSparkles size={14} /> Create Content
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 max-h-[600px] overflow-y-auto">
                {drafts.map((draft) => (
                  <div
                    key={draft.id}
                    className={`p-4 transition cursor-pointer flex items-start gap-3 ${
                      selectedDraft?.id === draft.id
                        ? 'bg-studio-50 border-l-3 border-l-studio-600'
                        : 'hover:bg-gray-50'
                    }`}
                    onClick={() => { setSelectedDraft(draft); setPublishResult(null); setCarouselIdx(0); }}
                  >
                    <div className={`w-3 h-3 rounded-full flex-shrink-0 mt-1.5 ${
                      selectedDraft?.id === draft.id ? 'bg-studio-600' : 'bg-gray-200'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm text-gray-900 truncate">{draft.title || draft.topic}</div>
                      <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{draft.content}</div>
                      <div className="text-xs text-gray-400 mt-1.5 flex items-center gap-2">
                        <IconCalendar size={12} />
                        {draft.created_at ? new Date(draft.created_at).toLocaleDateString() : 'N/A'}
                        {draft.content_type === 'carousel' ? (
                          <span className="inline-flex items-center gap-0.5 text-teal-600"><IconLayers size={11} /> Carousel{draft.carousel_slides ? ` · ${draft.carousel_slides.length} slides` : ''}</span>
                        ) : draft.content_type === 'poll' ? (
                          <span className="inline-flex items-center gap-0.5 text-green-600"><IconPoll size={11} /> Poll</span>
                        ) : draft.content_type === 'newsletter' ? (
                          <span className="inline-flex items-center gap-0.5 text-indigo-600"><IconNewspaper size={11} /> Newsletter</span>
                        ) : draft.content_type === 'video' || draft.media?.video?.filename ? (
                          <span className="inline-flex items-center gap-0.5 text-red-600"><IconVideo size={11} /> Video</span>
                        ) : draft.content_type === 'image' || draft.media?.image?.filename ? (
                          <span className="inline-flex items-center gap-0.5 text-purple-600"><IconImage size={11} /> Image</span>
                        ) : (
                          <span className="inline-flex items-center gap-0.5 text-blue-600"><IconCreate size={11} /> Text</span>
                        )}
                        {draft.status === 'published' && (
                          <span className="badge-published ml-1">Published</span>
                        )}
                      </div>
                    </div>
                    <div className="flex-shrink-0 ml-1">
                      {pendingDeleteId === draft.id ? (
                        <div className="flex items-center gap-1">
                          <button onClick={(e) => { e.stopPropagation(); handleDelete(draft.id); setPendingDeleteId(null); }}
                            className="px-2 py-1 bg-red-600 text-white rounded-lg text-xs font-medium">Yes</button>
                          <button onClick={(e) => { e.stopPropagation(); setPendingDeleteId(null); }}
                            className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium">No</button>
                        </div>
                      ) : (
                        <button onClick={(e) => { e.stopPropagation(); setPendingDeleteId(draft.id); }}
                          className="p-1 text-gray-300 hover:text-red-500 transition" title="Delete draft">
                          <IconTrash size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Preview & Publish */}
        <div className="lg:col-span-2 space-y-4">
          {selectedDraft ? (
            <>
              {/* Post details */}
              <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-gray-900">Review Post</h2>
                  <span className={`badge-${selectedDraft.status || 'draft'}`}>{selectedDraft.status || 'draft'}</span>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    {selectedDraft.title && (
                      <div>
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Title</div>
                        <div className="text-sm text-gray-900">{selectedDraft.title}</div>
                      </div>
                    )}

                    <div>
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Content <span className="text-gray-400 normal-case">({selectedDraft.content?.length || 0}/3000)</span></div>
                      <div className="p-3 bg-gray-50 rounded-xl border border-gray-100 text-sm text-gray-900 whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {selectedDraft.content}
                      </div>
                    </div>

                    {selectedDraft.hashtags?.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Hashtags</div>
                        <div className="flex gap-1.5 flex-wrap">
                          {selectedDraft.hashtags.map((tag, i) => (
                            <span key={i} className="bg-studio-50 text-studio-700 px-2.5 py-0.5 rounded-full text-xs font-medium">{tag}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {selectedDraft.cta && (
                      <div>
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Call to Action</div>
                        <div className="text-sm text-gray-900">{selectedDraft.cta}</div>
                      </div>
                    )}

                    {selectedDraft.media?.image?.filename && (
                      <div>
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Attached Image</div>
                        <img
                          src={getMediaFileUrl(selectedDraft.media.image.filename)}
                          alt={selectedDraft.media.image.alt_text || 'Generated image'}
                          className="w-full rounded-xl border border-gray-200"
                        />
                        {selectedDraft.media.image.provider && (
                          <div className="text-xs text-gray-400 mt-1">Provider: {selectedDraft.media.image.provider}</div>
                        )}
                      </div>
                    )}

                    {selectedDraft.media?.video?.filename && (
                      <div>
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Attached Video</div>
                        <video
                          controls
                          className="w-full rounded-xl border border-gray-200"
                          src={getMediaFileUrl(selectedDraft.media.video.filename)}
                        />
                        {selectedDraft.media.video.provider && (
                          <div className="text-xs text-gray-400 mt-1">Provider: {selectedDraft.media.video.provider} | Duration: {selectedDraft.media.video.duration}s</div>
                        )}
                      </div>
                    )}

                    {selectedDraft.carousel_slides?.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Carousel Slides ({selectedDraft.carousel_slides.length})</div>
                        <div className="border border-teal-200 rounded-xl overflow-hidden">
                          <div className="bg-teal-50 p-4">
                            <div className="flex items-center justify-between mb-2">
                              <button onClick={() => setCarouselIdx(Math.max(0, carouselIdx - 1))} disabled={carouselIdx === 0} className="p-1 hover:bg-teal-100 rounded-lg disabled:opacity-30 transition">
                                <IconChevronLeft size={16} className="text-teal-600" />
                              </button>
                              <span className="text-xs font-semibold text-teal-700">{carouselIdx + 1} / {selectedDraft.carousel_slides.length}</span>
                              <button onClick={() => setCarouselIdx(Math.min(selectedDraft.carousel_slides.length - 1, carouselIdx + 1))} disabled={carouselIdx >= selectedDraft.carousel_slides.length - 1} className="p-1 hover:bg-teal-100 rounded-lg disabled:opacity-30 transition">
                                <IconChevronRight size={16} className="text-teal-600" />
                              </button>
                            </div>
                            {(() => {
                              const slide = selectedDraft.carousel_slides[carouselIdx];
                              return (
                                <div className="bg-white rounded-xl p-4 border border-teal-100">
                                  <div className="font-semibold text-sm text-gray-900 mb-1">Slide {slide.slide_num || carouselIdx + 1}: {slide.heading}</div>
                                  {slide.body && <div className="text-xs text-gray-700 mb-2">{slide.body}</div>}
                                  {slide.bullets?.length > 0 && (
                                    <ul className="text-xs text-gray-600 space-y-0.5 list-disc pl-4">
                                      {slide.bullets.map((b, j) => <li key={j}>{b}</li>)}
                                    </ul>
                                  )}
                                  {slide.image_url && <img src={slide.image_url} alt={slide.heading} className="mt-2 rounded-lg w-full border border-gray-200" />}
                                  {!slide.image_url && slide.visual_prompt && (
                                    <div className="mt-2 p-2 bg-gray-50 rounded-lg text-xs text-gray-500 italic">Prompt: {slide.visual_prompt}</div>
                                  )}
                                </div>
                              );
                            })()}
                          </div>
                          <div className="flex gap-1 p-2 bg-gray-50 overflow-x-auto">
                            {selectedDraft.carousel_slides.map((s, i) => (
                              <button key={i} onClick={() => setCarouselIdx(i)} className={`flex-shrink-0 px-2 py-1 text-xs rounded-lg font-medium transition ${i === carouselIdx ? 'bg-teal-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-teal-50'}`}>
                                {i + 1}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {selectedDraft.poll_question && (
                      <div>
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Poll</div>
                        <div className="p-3 bg-green-50 border border-green-100 rounded-xl">
                          <div className="text-sm font-semibold text-gray-900 mb-2">{selectedDraft.poll_question}</div>
                          <div className="space-y-1.5">
                            {(selectedDraft.poll_options || []).map((opt, i) => (
                              <div key={i} className="text-xs bg-white border border-green-100 rounded-lg px-2.5 py-1.5 text-gray-700">
                                {opt}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="hidden lg:block">
                    <LinkedInPreview
                      title={selectedDraft.title}
                      content={selectedDraft.content}
                      hashtags={selectedDraft.hashtags}
                      cta={selectedDraft.cta}
                      image={selectedDraft.media?.image?.filename ? { filename: selectedDraft.media.image.filename } : null}
                      video={selectedDraft.media?.video?.filename ? { filename: selectedDraft.media.video.filename } : null}
                      poll={selectedDraft.poll_question ? { question: selectedDraft.poll_question, options: selectedDraft.poll_options || [] } : null}
                    />
                    {selectedDraft.carousel_slides?.length > 0 && (
                      <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-xl">
                        <div className="text-xs font-semibold text-gray-500 mb-2">Carousel Preview</div>
                        <div className="flex gap-2 overflow-x-auto pb-1">
                          {selectedDraft.carousel_slides.map((s, i) => (
                            <div key={i} className="flex-shrink-0 w-32 p-2 bg-white border border-gray-200 rounded-lg">
                              <div className="text-xs font-semibold text-gray-900 line-clamp-1">{s.heading}</div>
                              <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">{s.body}</div>
                              <div className="text-xs text-gray-400 mt-1">Slide {s.slide_num || i + 1}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Publish action */}
              {publishResult ? (
                <div className={`rounded-2xl border p-5 space-y-3 ${
                  publishResult.linkedin_post_id?.startsWith('local-')
                    ? 'bg-yellow-50 border-yellow-200'
                    : 'bg-green-50 border-green-200'
                }`}>
                  {publishResult.linkedin_post_id?.startsWith('local-') ? (
                    <>
                      <div className="text-base font-bold text-yellow-700 flex items-center gap-2">
                        <IconCalendar size={18} /> Saved Locally
                      </div>
                      <p className="text-sm text-yellow-800">
                        LinkedIn credentials are not configured.{' '}
                        <a href="/admin/settings" className="text-studio-600 hover:underline font-medium">Connect LinkedIn in Settings</a>{' '}
                        to publish directly.
                      </p>
                      <div className="flex gap-2 flex-wrap">
                        <button
                          onClick={() => {
                            const text = [selectedDraft.content, selectedDraft.cta, selectedDraft.hashtags?.join(' ')].filter(Boolean).join('\n\n');
                            navigator.clipboard.writeText(text);
                            setSuccess('Copied to clipboard!');
                          }}
                          className="btn-primary !text-sm"
                        >
                          Copy Post to Clipboard
                        </button>
                        <a href="https://www.linkedin.com/feed/" target="_blank" rel="noreferrer"
                          className="btn-secondary !text-sm">
                          Open LinkedIn Feed
                        </a>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="text-base font-bold text-green-700 flex items-center gap-2">
                        <IconCheckCircle size={18} /> Posted to LinkedIn!
                      </div>
                      {publishResult.linkedin_url && (
                        <a href={publishResult.linkedin_url} target="_blank" rel="noreferrer" className="btn-primary !text-sm">
                          View on LinkedIn
                        </a>
                      )}
                    </>
                  )}
                  <div className="text-xs text-gray-500">Post ID: {publishResult.linkedin_post_id}</div>
                </div>
              ) : (
                <button
                  onClick={handlePublish}
                  disabled={publishing || !selectedDraft}
                  className="w-full py-3.5 rounded-2xl text-white font-semibold text-base
                    bg-gradient-to-r from-linkedin-600 to-linkedin-500
                    hover:from-linkedin-700 hover:to-linkedin-600
                    disabled:opacity-50 disabled:cursor-not-allowed
                    shadow-lg hover:shadow-xl transition-all duration-200
                    flex items-center justify-center gap-2"
                >
                  {publishing ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                      Publishing...
                    </>
                  ) : (
                    <>
                      <IconSend size={18} />
                      Publish to LinkedIn
                    </>
                  )}
                </button>
              )}
            </>
          ) : (
            <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-12 text-center">
              <IconQueue size={48} className="mx-auto text-gray-200 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Select a draft</h3>
              <p className="text-sm text-gray-500">Choose a draft from the left panel to preview and publish</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
