import { getMediaFileUrl } from '@/lib/api';
import React from 'react';

function MediaSkeleton({ label }) {
  return (
    <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 aspect-video flex items-center justify-center animate-pulse-soft">
      <div className="text-center text-gray-400">
        <div className="w-8 h-8 rounded-full bg-gray-200 mx-auto mb-2" />
        <div className="text-xs">{label}</div>
      </div>
    </div>
  );
}

export default function LinkedInPreview({
  type,
  title,
  content,
  hashtags = [],
  cta,
  profileUrl,
  image,
  video,
  poll,
  carousel,
  imageLoading,
  videoLoading,
}) {
  const renderPostText = (text) => {
    const src = text || 'Your post will appear here...';
    const parts = src.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        return <strong key={idx}>{part.slice(2, -2)}</strong>;
      }
      return <React.Fragment key={idx}>{part}</React.Fragment>;
    });
  };
  const handle = profileUrl ? profileUrl.replace(/https?:\/\/(www\.)?linkedin\.com\/in\/?/i, '').replace(/\/$/, '') : 'Your Name';
  const avatarChar = profileUrl ? handle.charAt(0).toUpperCase() : '?';
  const charCount = (content || '').length;
  const countColor = charCount >= 3000
    ? 'text-red-500 font-semibold'
    : charCount >= 2700
      ? 'text-amber-500'
      : 'text-gray-400';

  const badges = [];
  if (image) badges.push('Image');
  if (video) badges.push('Video');
  if (poll) badges.push('Poll');
  if (type === 'carousel' || carousel) badges.push('Carousel');

  return (
    <div className="rounded-2xl shadow-card border border-gray-100 bg-white overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-studio-50 to-linkedin-50">
        <span className="font-semibold text-sm text-gray-900">LinkedIn Preview</span>
        {badges.map(b => (
          <span key={b} className="text-xs bg-studio-100 text-studio-700 px-2 py-0.5 rounded-full font-medium">{b}</span>
        ))}
      </div>

      <div className="p-4">
        {profileUrl && (
          <div className="flex items-center gap-3 mb-4">
            <div className="w-11 h-11 rounded-full bg-gradient-to-br from-studio-600 to-linkedin-600 flex items-center justify-center text-white font-bold text-sm">{avatarChar}</div>
            <div>
              <div className="font-semibold text-sm text-gray-900">{handle}</div>
              <div className="text-xs text-gray-500">Just now</div>
            </div>
          </div>
        )}

        {title && <div className="font-semibold text-sm mb-2 text-gray-900">{title}</div>}
        <div className="whitespace-pre-wrap text-sm text-gray-800 leading-relaxed">{renderPostText(content)}</div>

        {hashtags.length > 0 && <div className="mt-3 text-linkedin-600 text-sm font-medium">{hashtags.join(' ')}</div>}
        {cta && <div className="mt-3 font-medium text-sm text-gray-900">{cta}</div>}

        {image && (
          <div className="mt-4 rounded-xl overflow-hidden border border-gray-200">
            <img src={getMediaFileUrl(image.filename)} alt="Post image" className="w-full h-auto" />
          </div>
        )}
        {!image && imageLoading && <MediaSkeleton label="Generating image..." />}

        {video && (
          <div className="mt-4 rounded-xl overflow-hidden border border-gray-200 bg-gray-900">
            <video controls className="w-full" src={video.url || getMediaFileUrl(video.filename)} />
          </div>
        )}
        {!video && videoLoading && <MediaSkeleton label="Rendering video..." />}

        {poll && poll.question && (
          <div className="mt-4 border border-gray-200 rounded-xl overflow-hidden">
            <div className="p-3 bg-gray-50">
              <p className="font-semibold text-sm text-gray-900">{poll.question}</p>
            </div>
            <div className="p-3 space-y-2">
              {(poll.options || []).filter(Boolean).map((opt, i) => (
                <div key={i} className="bg-studio-50 border border-studio-100 rounded-lg px-4 py-2 text-sm text-gray-800 hover:bg-studio-100 transition cursor-pointer">{opt}</div>
              ))}
            </div>
          </div>
        )}

        {(type === 'carousel' || carousel) && (
          <div className="mt-4">
            <div className="bg-gradient-to-br from-studio-600 to-linkedin-600 rounded-xl p-6 text-white min-h-[160px] flex flex-col justify-center items-center">
              <div className="text-lg font-bold text-center">Carousel Post</div>
              <div className="text-sm opacity-80 mt-2">Swipe through slides</div>
              <div className="flex gap-1.5 mt-4">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className={`w-2 h-2 rounded-full ${i === 1 ? 'bg-white' : 'bg-white/40'}`} />
                ))}
              </div>
            </div>
          </div>
        )}

        <div className={`mt-3 text-xs ${countColor}`}>{charCount}/3000 chars</div>
        {profileUrl && <a href={profileUrl} target="_blank" rel="noreferrer" className="block mt-2 text-xs text-studio-600 hover:underline">View your LinkedIn profile</a>}
      </div>

      <div className="px-4 py-2.5 border-t border-gray-100 flex items-center gap-6 text-xs text-gray-500">
        <span className="hover:text-linkedin-600 cursor-pointer transition">&#128077; Like</span>
        <span className="hover:text-linkedin-600 cursor-pointer transition">&#128172; Comment</span>
        <span className="hover:text-linkedin-600 cursor-pointer transition">&#128257; Repost</span>
        <span className="hover:text-linkedin-600 cursor-pointer transition">&#9993;&#65039; Send</span>
      </div>
    </div>
  );
}
