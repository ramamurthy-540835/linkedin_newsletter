export default function LinkedInPreview({ title, content, hashtags=[], cta, profileUrl }) {
  const handle = profileUrl ? profileUrl.replace(/https?:\/\/(www\.)?linkedin\.com\/in\/?/i, '').replace(/\/$/, '') : 'Your Name';
  const avatarChar = profileUrl ? handle.charAt(0).toUpperCase() : '?';

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="font-bold mb-4">LinkedIn Preview</div>
      {profileUrl && (
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-blue-700 flex items-center justify-center text-white font-bold text-sm">{avatarChar}</div>
          <div>
            <div className="font-semibold text-sm">{handle}</div>
            <div className="text-xs text-gray-500">Just now · 🌐</div>
          </div>
        </div>
      )}
      {title&&<div className="font-semibold mb-2">{title}</div>}
      <div className="whitespace-pre-wrap text-sm">{content||'Your post will appear here...'}</div>
      {hashtags.length>0&&<div className="mt-3 text-blue-700 text-sm">{hashtags.join(' ')}</div>}
      {cta&&<div className="mt-3 font-medium text-sm">{cta}</div>}
      <div className="mt-3 text-xs text-gray-500">{(content||'').length}/3000 chars</div>
      {profileUrl && <a href={profileUrl} target="_blank" rel="noreferrer" className="block mt-3 text-xs text-blue-700 hover:underline">View your LinkedIn profile ↗</a>}
    </div>
  );
}
