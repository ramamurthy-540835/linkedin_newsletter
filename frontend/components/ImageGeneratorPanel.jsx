'use client';
import { useState } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Select from '@/components/Select';
import Textarea from '@/components/Textarea';
import { generateImage, getMediaFileUrl } from '@/lib/api';

const IMAGE_STYLES = [
  { value: 'corporate', label: 'Corporate' },
  { value: 'modern_saas', label: 'Modern SaaS' },
  { value: 'infographic', label: 'Infographic' },
  { value: 'futuristic_ai', label: 'Futuristic AI' },
  { value: 'professional_business', label: 'Professional Business' },
  { value: 'minimal', label: 'Minimal' },
  { value: 'linkedin_brand', label: 'LinkedIn Personal Brand' },
];

const ASPECT_RATIOS = [
  { value: 'square', label: 'Square (1:1)' },
  { value: 'portrait', label: 'Portrait (9:16)' },
  { value: 'landscape', label: 'Landscape (16:9)' },
];

const PROVIDERS = [
  { value: 'imagen', label: 'Google Imagen 3' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'openai', label: 'OpenAI DALL-E 3' },
];

export default function ImageGeneratorPanel({ onAttach, postContent = '' }) {
  const [prompt, setPrompt] = useState(postContent ? `Professional image for: ${postContent.slice(0, 200)}` : '');
  const [style, setStyle] = useState('corporate');
  const [aspectRatio, setAspectRatio] = useState('landscape');
  const [provider, setProvider] = useState('imagen');
  const [brandColors, setBrandColors] = useState('');
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);

  const generate = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await generateImage({
        prompt: prompt.trim(),
        style,
        aspect_ratio: aspectRatio,
        provider,
        brand_colors: brandColors,
        count: 2,
      });
      setImages(result.images || []);
      if (result.images?.length > 0) {
        setSelectedImage(result.images[0]);
      }
    } catch (e) {
      setError(e.message || 'Image generation failed');
    } finally {
      setLoading(false);
    }
  };

  const downloadImage = (img) => {
    const url = getMediaFileUrl(img.filename);
    const a = document.createElement('a');
    a.href = url;
    a.download = img.filename;
    a.click();
  };

  return (
    <div className="space-y-4">
      <Card title="Image Generation" subtitle="Create AI-generated visuals for your post">
        <div className="space-y-4">
          <Textarea
            label="Image Prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            placeholder="Describe the image you want to generate..."
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select label="Visual Style" value={style} onChange={(e) => setStyle(e.target.value)} options={IMAGE_STYLES} />
            <Select label="Aspect Ratio" value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)} options={ASPECT_RATIOS} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select label="Provider" value={provider} onChange={(e) => setProvider(e.target.value)} options={PROVIDERS} />
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Brand Colors</label>
              <input
                type="text"
                value={brandColors}
                onChange={(e) => setBrandColors(e.target.value)}
                placeholder="#0A66C2, #FFFFFF"
                className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-linkedin-500 focus:border-linkedin-500 transition"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <Button onClick={generate} disabled={loading || !prompt.trim()} variant="primary" loading={loading} className="flex-1">
              {loading ? 'Generating...' : 'Generate Image'}
            </Button>
            {images.length > 0 && (
              <Button onClick={generate} disabled={loading} variant="outline">
                Regenerate
              </Button>
            )}
          </div>

          {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>}
        </div>
      </Card>

      {images.length > 0 && (
        <Card title="Generated Images" subtitle="Click to select, then attach to your post">
          <div className="grid grid-cols-2 gap-4">
            {images.map((img, i) => (
              <div
                key={i}
                onClick={() => setSelectedImage(img)}
                className={`relative rounded-xl overflow-hidden border-2 cursor-pointer transition-all ${
                  selectedImage?.filename === img.filename
                    ? 'border-linkedin-600 shadow-lg ring-2 ring-linkedin-200'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <img
                  src={getMediaFileUrl(img.filename)}
                  alt={`Generated ${i + 1}`}
                  className="w-full h-auto"
                />
                {selectedImage?.filename === img.filename && (
                  <div className="absolute top-2 right-2 bg-linkedin-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs">
                    &#10003;
                  </div>
                )}
              </div>
            ))}
          </div>

          {selectedImage && (
            <div className="flex gap-3 mt-4">
              <Button onClick={() => downloadImage(selectedImage)} variant="outline" className="flex-1">
                Download
              </Button>
              {onAttach && (
                <Button onClick={() => onAttach(selectedImage)} variant="primary" className="flex-1">
                  Attach to Post
                </Button>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
