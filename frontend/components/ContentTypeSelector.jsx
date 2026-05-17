'use client';

const CONTENT_TYPES = [
  { value: 'text', label: 'Text Post', icon: '📝' },
  { value: 'image', label: 'Image Post', icon: '🖼️' },
  { value: 'video', label: 'Video Post', icon: '🎬' },
  { value: 'carousel', label: 'Carousel', icon: '📑' },
  { value: 'poll', label: 'Poll', icon: '📊' },
  { value: 'newsletter', label: 'Newsletter', icon: '📰' },
];

export default function ContentTypeSelector({ value, onChange }) {
  return (
    <div className="bg-white rounded-xl shadow-card border border-gray-100 p-2 mb-6">
      <div className="flex flex-wrap gap-1">
        {CONTENT_TYPES.map((type) => (
          <button
            key={type.value}
            onClick={() => onChange(type.value)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
              value === type.value
                ? 'bg-linkedin-600 text-white shadow-md'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <span className="text-base">{type.icon}</span>
            <span className="hidden sm:inline">{type.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
