'use client';
import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Input from '@/components/Input';
import Textarea from '@/components/Textarea';
import Select from '@/components/Select';
import Modal from '@/components/Modal';
import LinkedInPreview from '@/components/LinkedInPreview';
import {
  IconLinkedIn,
  IconSparkles,
  IconCreate,
  IconImage,
  IconVideo,
  IconLayers,
  IconPoll,
  IconNewspaper,
  IconLightbulb,
  IconMegaphone,
  IconRocket,
  IconUsers,
  IconTarget,
  IconZap,
} from '@/components/icons';
import {
  savePost,
  generateContentPlan,
  generateImage,
  startVideoGeneration,
  getMediaJobStatus,
  getMediaFileUrl,
  aiGenerate,
} from '@/lib/api';

const CONTENT_TYPES = [
  { value: 'text', label: 'Text Post', icon: IconCreate, desc: 'Standard LinkedIn post', color: 'blue' },
  { value: 'thought_leadership', label: 'Thought Leadership', icon: IconLightbulb, desc: 'Expert insights & opinions', color: 'amber' },
  { value: 'image', label: 'Image Post', icon: IconImage, desc: 'Post with AI-generated visual', color: 'purple' },
  { value: 'video', label: 'Video Post', icon: IconVideo, desc: 'Post with AI-generated video', color: 'red' },
  { value: 'carousel', label: 'Carousel', icon: IconLayers, desc: 'Multi-slide storytelling', color: 'teal' },
  { value: 'poll', label: 'Poll', icon: IconPoll, desc: 'Engage with questions', color: 'green' },
  { value: 'newsletter', label: 'Newsletter', icon: IconNewspaper, desc: 'Long-form article', color: 'indigo' },
  { value: 'event_promotion', label: 'Event Promotion', icon: IconMegaphone, desc: 'Promote events & webinars', color: 'pink' },
  { value: 'product_launch', label: 'Product Launch', icon: IconRocket, desc: 'Announce products & features', color: 'orange' },
  { value: 'hiring', label: 'Hiring Post', icon: IconUsers, desc: 'Recruit top talent', color: 'cyan' },
];

const TONES = [
  { value: 'professional', label: 'Professional' },
  { value: 'thought-leader', label: 'Thought Leader' },
  { value: 'educational', label: 'Educational' },
  { value: 'storytelling', label: 'Storytelling' },
  { value: 'casual', label: 'Casual' },
  { value: 'inspirational', label: 'Inspirational' },
  { value: 'humorous', label: 'Humorous' },
  { value: 'data-driven', label: 'Data-Driven' },
];

const GOALS = [
  { value: 'engagement', label: 'Engagement' },
  { value: 'awareness', label: 'Brand Awareness' },
  { value: 'leads', label: 'Lead Generation' },
  { value: 'hiring', label: 'Hiring' },
  { value: 'thought_leadership', label: 'Thought Leadership' },
  { value: 'community', label: 'Community Building' },
];

const VISUAL_STYLES = [
  { value: 'corporate', label: 'Corporate' },
  { value: 'modern_saas', label: 'Modern SaaS' },
  { value: 'infographic', label: 'Infographic' },
  { value: 'futuristic_ai', label: 'Futuristic AI' },
  { value: 'professional_business', label: 'Professional Business' },
  { value: 'minimal', label: 'Minimal' },
  { value: 'linkedin_brand', label: 'LinkedIn Personal Brand' },
];

const ASPECT_RATIOS = [
  { value: '16:9', label: 'Landscape (16:9)' },
  { value: '1:1', label: 'Square (1:1)' },
  { value: '9:16', label: 'Portrait (9:16)' },
];

const IMAGE_PROVIDERS = [
  { value: 'xai-image', label: 'xAI Image Generation' },
];

const VIDEO_PROVIDERS = [
  { value: 'xai-video', label: 'xAI Video Generation' },
];

const VIDEO_DURATIONS = [
  { value: '15', label: '15 sec' },
  { value: '30', label: '30 sec' },
  { value: '60', label: '60 sec' },
];

const VIDEO_STYLES = [
  { value: 'corporate', label: 'Corporate' },
  { value: 'tech_demo', label: 'Tech Demo' },
  { value: 'storytelling', label: 'Storytelling' },
  { value: 'explainer', label: 'Explainer' },
  { value: 'social_media', label: 'Social Media' },
];

const COLOR_MAP = {
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', activeBorder: 'border-blue-500', text: 'text-blue-600', activeBg: 'bg-blue-50', ring: 'ring-blue-200' },
  amber: { bg: 'bg-amber-50', border: 'border-amber-200', activeBorder: 'border-amber-500', text: 'text-amber-600', activeBg: 'bg-amber-50', ring: 'ring-amber-200' },
  purple: { bg: 'bg-purple-50', border: 'border-purple-200', activeBorder: 'border-purple-500', text: 'text-purple-600', activeBg: 'bg-purple-50', ring: 'ring-purple-200' },
  red: { bg: 'bg-red-50', border: 'border-red-200', activeBorder: 'border-red-500', text: 'text-red-600', activeBg: 'bg-red-50', ring: 'ring-red-200' },
  teal: { bg: 'bg-teal-50', border: 'border-teal-200', activeBorder: 'border-teal-500', text: 'text-teal-600', activeBg: 'bg-teal-50', ring: 'ring-teal-200' },
  green: { bg: 'bg-green-50', border: 'border-green-200', activeBorder: 'border-green-500', text: 'text-green-600', activeBg: 'bg-green-50', ring: 'ring-green-200' },
  indigo: { bg: 'bg-indigo-50', border: 'border-indigo-200', activeBorder: 'border-indigo-500', text: 'text-indigo-600', activeBg: 'bg-indigo-50', ring: 'ring-indigo-200' },
  pink: { bg: 'bg-pink-50', border: 'border-pink-200', activeBorder: 'border-pink-500', text: 'text-pink-600', activeBg: 'bg-pink-50', ring: 'ring-pink-200' },
  orange: { bg: 'bg-orange-50', border: 'border-orange-200', activeBorder: 'border-orange-500', text: 'text-orange-600', activeBg: 'bg-orange-50', ring: 'ring-orange-200' },
  cyan: { bg: 'bg-cyan-50', border: 'border-cyan-200', activeBorder: 'border-cyan-500', text: 'text-cyan-600', activeBg: 'bg-cyan-50', ring: 'ring-cyan-200' },
};

const LINKEDIN_PROFILE_KEY = 'linkedin_profile_url';

function GenerationProgress({ steps }) {
  return (
    <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5">
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
              step.status === 'done' ? 'bg-green-100 text-green-700' :
              step.status === 'active' ? 'bg-studio-100 text-studio-700 animate-pulse-soft' :
              step.status === 'error' ? 'bg-red-100 text-red-700' :
              'bg-gray-100 text-gray-400'
            }`}>
              {step.status === 'done' ? '✓' : step.status === 'error' ? '!' : i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-medium ${
                step.status === 'active' ? 'text-studio-700' :
                step.status === 'done' ? 'text-green-700' :
                step.status === 'error' ? 'text-red-700' :
                'text-gray-400'
              }`}>{step.label}</div>
              {step.detail && <div className="text-xs text-gray-500 truncate">{step.detail}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProfileSetupModal({ onSave, onSkip, existing }) {
  const [url, setUrl] = useState(existing || '');
  const [error, setError] = useState('');

  const validate = (val) => {
    if (!val) return 'Please enter your LinkedIn profile URL.';
    if (!/linkedin\.com\/in\//i.test(val)) return 'Must be a LinkedIn profile URL';
    return '';
  };

  const handleSave = () => {
    const err = validate(url.trim());
    if (err) { setError(err); return; }
    onSave(url.trim());
  };

  return (
    <Modal title="Connect your LinkedIn" onClose={onSkip}>
      <div className="space-y-4">
        <label className="block text-sm font-semibold text-gray-700">Your LinkedIn Profile URL</label>
        <input type="url" placeholder="https://www.linkedin.com/in/yourname" value={url}
          onChange={e => { setUrl(e.target.value); setError(''); }}
          onKeyDown={e => e.key === 'Enter' && handleSave()}
          className={`input-field font-mono ${error ? '!border-red-500' : ''}`}
          autoFocus />
        {error && <div className="text-red-500 text-xs">{error}</div>}
        <div className="flex gap-3 pt-2">
          <Button onClick={handleSave} variant="primary" className="flex-1">Save Profile</Button>
          <Button onClick={onSkip} variant="ghost" className="border border-gray-200">Skip for now</Button>
        </div>
      </div>
    </Modal>
  );
}

function CreatePageContent() {
  const searchParams = useSearchParams();

  // Form state
  const [topic, setTopic] = useState('');
  const [audience, setAudience] = useState('');
  const [tone, setTone] = useState('professional');
  const [contentType, setContentType] = useState('text');
  const [goal, setGoal] = useState('engagement');
  const [ctaInput, setCtaInput] = useState('');
  const [keywords, setKeywords] = useState('');
  const [writingStyle, setWritingStyle] = useState('');
  const [brandColors, setBrandColors] = useState('');
  const [visualStyle, setVisualStyle] = useState('corporate');
  const [aspectRatio, setAspectRatio] = useState('16:9');

  // Media checkboxes
  const [generateImg, setGenerateImg] = useState(false);
  const [generateVid, setGenerateVid] = useState(false);

  // Image options
  const [imageProvider, setImageProvider] = useState('xai-image');
  const [imagePrompt, setImagePrompt] = useState('');

  // Video options
  const [videoProvider, setVideoProvider] = useState('xai-video');
  const [videoDuration, setVideoDuration] = useState('30');
  const [videoStyle, setVideoStyle] = useState('corporate');
  const [videoScript, setVideoScript] = useState('');

  // Generated content
  const [postText, setPostText] = useState('');
  const [hashtags, setHashtags] = useState([]);
  const [cta, setCta] = useState('');
  const [suggestedTitle, setSuggestedTitle] = useState('');
  const [altText, setAltText] = useState('');
  const [carouselSlides, setCarouselSlides] = useState([]);
  const [pollQuestion, setPollQuestion] = useState('');
  const [pollOptions, setPollOptions] = useState([]);

  // Media results
  const [generatedImages, setGeneratedImages] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [videoJobId, setVideoJobId] = useState(null);
  const [videoResult, setVideoResult] = useState(null);

  // UI state
  const [busy, setBusy] = useState(false);
  const [steps, setSteps] = useState([]);
  const [error, setError] = useState('');
  const [profileUrl, setProfileUrl] = useState('');
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [videoLoading, setVideoLoading] = useState(false);
  const [aiCompleting, setAiCompleting] = useState(false);
  const [prefillNotice, setPrefillNotice] = useState('');

  const pollRef = useRef(null);
  const autofillRef = useRef(null);
  const autofillSeqRef = useRef(0);
  const hasPrefilledRef = useRef(false);

  const prefillMetadataFromXAI = async (topicValue, hookValue = '', sourceContentType = contentType) => {
    const t = (topicValue || '').trim();
    if (!t) return null;
    const out = await aiGenerate({
      system: "Return strict JSON only. No markdown.",
      prompt: `Given this LinkedIn content topic, generate recommended metadata fields only. Do not generate full post content.
Topic: ${t}
Hook Context: ${hookValue || ''}
Content Type: ${sourceContentType}
Return ONLY valid JSON:
{
  "targetAudience": "",
  "tone": "",
  "goal": "",
  "callToAction": "",
  "keywords": [],
  "writingStyle": "",
  "visualStyle": "",
  "brandColors": ["#0A66C2", "#FFFFFF"],
  "hashtags": [],
  "pollQuestion": "",
  "pollOptions": [],
  "carouselSlides": []
}`,
    });
    let pkg = {};
    try { pkg = JSON.parse((out?.text || "{}").replace(/```json|```/g, "").trim()); } catch {}
    return pkg;
  };

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    return () => {
      if (autofillRef.current) clearTimeout(autofillRef.current);
    };
  }, []);

  useEffect(() => {
    const saved = typeof window !== 'undefined' ? localStorage.getItem(LINKEDIN_PROFILE_KEY) : '';
    setProfileUrl(saved || '');
    if (!saved) setShowProfileModal(true);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const topicParam = searchParams.get('topic');
    const prefillParam = searchParams.get('prefill') === 'true';
    const hookParam = searchParams.get('hook');
    const type = searchParams.get('type');
    console.log("CREATE_PREFILL_PARAMS", { topicParam, prefillParam, hookParam, type });
    if (type && CONTENT_TYPES.some(ct => ct.value === type)) {
      setContentType(type);
      if (type === 'image') setGenerateImg(true);
      if (type === 'video') setGenerateVid(true);
    }
    if (topicParam) {
      const decodedTopic = decodeURIComponent(topicParam);
      setTopic(decodedTopic);
      if (hookParam) setSuggestedTitle(decodeURIComponent(hookParam));
      if (prefillParam && !hasPrefilledRef.current) {
        hasPrefilledRef.current = true;
        (async () => {
          setAiCompleting(true);
          setError('');
          setPrefillNotice('xAI is auto-filling recommended settings...');
          try {
            const result = await prefillMetadataFromXAI(decodedTopic, decodeURIComponent(hookParam || ''), type || contentType);
            console.log("CREATE_PREFILL_RESULT", result);
            if (!audience?.trim() && result?.targetAudience) setAudience(result.targetAudience);
            if ((!tone || tone === 'professional') && result?.tone) setTone(result.tone);
            if ((!goal || goal === 'engagement') && result?.goal) setGoal(result.goal);
            if (!ctaInput?.trim() && result?.callToAction) setCtaInput(result.callToAction);
            if (!keywords?.trim() && Array.isArray(result?.keywords)) setKeywords(result.keywords.join(', '));
            if (!writingStyle?.trim() && result?.writingStyle) setWritingStyle(result.writingStyle);
            if ((!visualStyle || visualStyle === 'corporate') && result?.visualStyle) setVisualStyle(result.visualStyle);
            if (!brandColors?.trim() && Array.isArray(result?.brandColors)) setBrandColors(result.brandColors.join(', '));
            if ((!hashtags || hashtags.length === 0) && Array.isArray(result?.hashtags)) setHashtags(result.hashtags);
            if ((type || contentType) === 'poll') {
              if (!pollQuestion?.trim() && result?.pollQuestion) setPollQuestion(result.pollQuestion);
              if ((!pollOptions || pollOptions.length === 0) && Array.isArray(result?.pollOptions)) setPollOptions(result.pollOptions);
            }
            if ((type || contentType) === 'carousel' && (!carouselSlides || carouselSlides.length === 0) && Array.isArray(result?.carouselSlides)) {
              setCarouselSlides(result.carouselSlides);
            }
            setPrefillNotice('xAI filled recommended settings. Review and click Generate Content.');
          } catch (e) {
            setError(e?.message || 'xAI metadata prefill failed');
            setPrefillNotice('xAI metadata prefill failed.');
          } finally {
            setAiCompleting(false);
          }
        })();
      }
    }
  }, [searchParams]);

  useEffect(() => {
    const t = (topic || '').trim();
    if (!t) return;
    if (busy) return;

    if (autofillRef.current) clearTimeout(autofillRef.current);
    autofillRef.current = setTimeout(async () => {
      const seq = ++autofillSeqRef.current;
      setAiCompleting(true);
      setPrefillNotice('xAI is auto-filling recommended settings...');
      try {
        const out = await aiGenerate({
          system: "Return strict JSON only. No markdown.",
          prompt: `Given this LinkedIn content topic, generate recommended metadata fields only. Do not generate full post content.
Topic: ${t}
Content Type: ${contentType}
Return ONLY valid JSON:
{
  "targetAudience": "",
  "tone": "",
  "goal": "",
  "callToAction": "",
  "keywords": [],
  "writingStyle": "",
  "visualStyle": "",
  "brandColors": ["#0A66C2", "#FFFFFF"],
  "hashtags": [],
  "pollQuestion": "",
  "pollOptions": [],
  "carouselSlides": []
}`,
        });
        if (seq !== autofillSeqRef.current) return;
        let pkg = {};
        try { pkg = JSON.parse((out?.text || "{}").replace(/```json|```/g, "").trim()); } catch {}
        if (!audience?.trim() && pkg.targetAudience) setAudience(pkg.targetAudience);
        if ((!tone || tone === 'professional') && pkg.tone) setTone(pkg.tone);
        if ((!goal || goal === 'engagement') && pkg.goal) setGoal(pkg.goal);
        if (!ctaInput?.trim() && pkg.callToAction) setCtaInput(pkg.callToAction);
        if (!keywords?.trim() && Array.isArray(pkg.keywords)) setKeywords(pkg.keywords.join(', '));
        if (!writingStyle?.trim() && pkg.writingStyle) setWritingStyle(pkg.writingStyle);
        if ((!visualStyle || visualStyle === 'corporate') && pkg.visualStyle) setVisualStyle(pkg.visualStyle);
        if (!brandColors?.trim() && Array.isArray(pkg.brandColors)) setBrandColors(pkg.brandColors.join(', '));
        if ((!hashtags || hashtags.length === 0) && Array.isArray(pkg.hashtags)) setHashtags(pkg.hashtags);
        if (contentType === 'poll') {
          if (!pollQuestion?.trim() && pkg.pollQuestion) setPollQuestion(pkg.pollQuestion);
          if ((!pollOptions || pollOptions.length === 0) && Array.isArray(pkg.pollOptions)) setPollOptions(pkg.pollOptions);
        }
        if (contentType === 'carousel' && (!carouselSlides || carouselSlides.length === 0) && Array.isArray(pkg.carouselSlides)) {
          setCarouselSlides(pkg.carouselSlides);
        }
        setPrefillNotice('xAI filled recommended settings. Review and click Generate Content.');
      } catch {
        if (seq === autofillSeqRef.current) setPrefillNotice('Auto-fill could not complete. You can continue manually or click Generate Content.');
      } finally {
        if (seq === autofillSeqRef.current) setAiCompleting(false);
      }
    }, 700);
  }, [topic, contentType]);

  const saveProfile = (url) => {
    localStorage.setItem(LINKEDIN_PROFILE_KEY, url);
    setProfileUrl(url);
    setShowProfileModal(false);
  };

  const updateStep = (idx, patch) => {
    setSteps(prev => prev.map((s, i) => i === idx ? { ...s, ...patch } : s));
  };

  const generateAll = async () => {
    if (!topic.trim()) { setError('Please enter a topic'); return; }
    setError('');
    setBusy(true);
    setGeneratedImages([]);
    setSelectedImage(null);
    setVideoResult(null);
    setVideoJobId(null);

    const wantImage = generateImg || contentType === 'image';
    const wantVideo = generateVid || contentType === 'video';

    const newSteps = [{ label: 'Generating content plan...', status: 'active' }];
    if (wantImage) newSteps.push({ label: 'Generating image prompt...', status: 'pending' });
    if (wantImage) newSteps.push({ label: 'Generating image...', status: 'pending' });
    if (wantVideo) newSteps.push({ label: 'Generating video script...', status: 'pending' });
    if (wantVideo) newSteps.push({ label: 'Rendering video...', status: 'pending' });
    setSteps(newSteps);

    let stepIdx = 0;

    try {
      setAiCompleting(true);
      const completionPrompt = `Given this LinkedIn content topic, generate a complete publishing package.
Topic: ${topic.trim()}
Content Type: ${contentType}
Return ONLY valid JSON:
{
  "targetAudience": "",
  "tone": "",
  "goal": "",
  "callToAction": "",
  "keywords": [],
  "writingStyle": "",
  "visualStyle": "",
  "brandColors": ["#0A66C2", "#FFFFFF"],
  "hashtags": [],
  "post": "",
  "imagePrompt": "",
  "carouselSlides": []
}
Rules:
- Post must be 1200-2500 chars, LinkedIn-ready, professional, practical, and current.
- If Content Type is carousel, carouselSlides is REQUIRED and must include 4-7 slides with heading/body/bullets.`;
      const aiOut = await aiGenerate({
        prompt: completionPrompt,
        system: "Return strict JSON only. No markdown.",
      });
      let pkg = {};
      try { pkg = JSON.parse((aiOut?.text || "{}").replace(/```json|```/g, "").trim()); } catch {}

      // Preserve user-entered values; only fill missing fields.
      if (!audience?.trim() && pkg.targetAudience) setAudience(pkg.targetAudience);
      if ((!tone || tone === 'professional') && pkg.tone) setTone(pkg.tone);
      if ((!goal || goal === 'engagement') && pkg.goal) setGoal(pkg.goal);
      if (!ctaInput?.trim() && pkg.callToAction) setCtaInput(pkg.callToAction);
      if (!keywords?.trim() && Array.isArray(pkg.keywords)) setKeywords(pkg.keywords.join(', '));
      if (!writingStyle?.trim() && pkg.writingStyle) setWritingStyle(pkg.writingStyle);
      if ((!visualStyle || visualStyle === 'corporate') && pkg.visualStyle) setVisualStyle(pkg.visualStyle);
      if (!brandColors?.trim() && Array.isArray(pkg.brandColors)) setBrandColors(pkg.brandColors.join(', '));
      if ((!hashtags || hashtags.length === 0) && Array.isArray(pkg.hashtags)) setHashtags(pkg.hashtags);
      if (!postText?.trim() && pkg.post) setPostText(pkg.post);
      if (wantImage && !imagePrompt?.trim() && pkg.imagePrompt) setImagePrompt(pkg.imagePrompt);
      if (contentType === 'carousel' && (!carouselSlides || carouselSlides.length === 0) && Array.isArray(pkg.carouselSlides)) {
        setCarouselSlides(pkg.carouselSlides);
      }
      if (!cta?.trim() && pkg.callToAction) setCta(pkg.callToAction);
      setAiCompleting(false);

      const plan = await generateContentPlan({
        topic: topic.trim(),
        audience: (audience || pkg.targetAudience || '').trim() || 'LinkedIn professionals',
        tone,
        contentType: contentType === 'image' ? 'text' : contentType === 'video' ? 'text' : contentType,
        brandColors,
        visualStyle,
        aspectRatio,
        generateImage: wantImage,
        generateVideo: wantVideo,
        imageProvider,
        videoProvider,
        videoDuration: parseInt(videoDuration),
        videoStyle,
      });

      if (!postText?.trim()) setPostText(plan.postText || '');
      if (!hashtags?.length) setHashtags(plan.hashtags || []);
      if (!cta?.trim()) setCta(plan.cta || '');
      setSuggestedTitle(plan.suggestedTitle || '');
      setAltText(plan.altText || '');
      if (plan.imagePrompt) setImagePrompt(plan.imagePrompt);
      if (plan.videoScript) setVideoScript(plan.videoScript);
      if (plan.carouselSlides) setCarouselSlides(plan.carouselSlides);
      if (plan.pollQuestion) setPollQuestion(plan.pollQuestion);
      if (plan.pollOptions) setPollOptions(plan.pollOptions);

      updateStep(stepIdx, { status: 'done', label: 'Content plan ready', detail: `${(plan.postText || '').length} chars` });
      stepIdx++;

      if (wantImage) {
        const imgPrompt = plan.imagePrompt || imagePrompt;
        if (!imgPrompt) {
          updateStep(stepIdx, { status: 'done', label: 'Image prompt from plan' });
          stepIdx++;
          updateStep(stepIdx, { status: 'error', label: 'No image prompt generated', detail: 'Enter one manually and click Generate Image' });
          stepIdx++;
        } else {
          setImagePrompt(imgPrompt);
          updateStep(stepIdx, { status: 'done', label: 'Image prompt ready' });
          stepIdx++;
          updateStep(stepIdx, { status: 'active', label: 'Generating image...' });
          setImageLoading(true);
          try {
            const imgResult = await generateImage({
              prompt: imgPrompt,
              style: visualStyle,
              aspect_ratio: aspectRatio === '16:9' ? 'landscape' : aspectRatio === '1:1' ? 'square' : 'portrait',
              provider: imageProvider,
              brand_colors: brandColors,
              count: 2,
            });
            const images = imgResult.images || [];
            setGeneratedImages(images);
            if (images.length > 0) setSelectedImage(images[0]);
            updateStep(stepIdx, { status: 'done', label: `${images.length} image(s) generated` });
          } catch (imgErr) {
            updateStep(stepIdx, { status: 'error', label: 'Image generation failed', detail: imgErr.message });
          } finally {
            setImageLoading(false);
          }
          stepIdx++;
        }
      }

      if (wantVideo) {
        const script = plan.videoScript || videoScript;
        if (script) setVideoScript(script);
        updateStep(stepIdx, { status: 'done', label: 'Video script ready' });
        stepIdx++;
        updateStep(stepIdx, { status: 'active', label: 'Rendering video...', detail: 'This may take a few minutes' });
        setVideoLoading(true);
        try {
          const vidResult = await startVideoGeneration({
            topic: topic.trim(),
            script: script || '',
            duration: parseInt(videoDuration),
            voice: 'none',
            captions: false,
            style: videoStyle,
          });
          setVideoJobId(vidResult.job_id);
          const vidStepIdx = stepIdx;
          startVideoPolling(vidResult.job_id, vidStepIdx);
        } catch (vidErr) {
          updateStep(stepIdx, { status: 'error', label: 'Video generation failed', detail: vidErr.message });
          setVideoLoading(false);
        }
      }

    } catch (e) {
      setAiCompleting(false);
      updateStep(stepIdx, { status: 'error', label: 'Content plan failed', detail: e.message });
      setError(e.message || 'Failed to generate content');
    } finally {
      setAiCompleting(false);
      setBusy(false);
    }
  };

  const startVideoPolling = (jobId, stepIdx) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await getMediaJobStatus(jobId);
        if (status.status === 'completed') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setVideoLoading(false);
          setVideoResult(status.result);
          updateStep(stepIdx, { status: 'done', label: 'Video ready', detail: status.result?.filename });
        } else if (status.status === 'failed') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setVideoLoading(false);
          updateStep(stepIdx, { status: 'error', label: 'Video failed', detail: status.message });
        } else {
          updateStep(stepIdx, { detail: status.message });
        }
      } catch {}
    }, 5000);
  };

  const generateImagePromptOnly = async () => {
    if (!topic.trim()) return;
    setError('');
    try {
      const plan = await generateContentPlan({
        topic: topic.trim(), audience, tone, contentType: 'text', brandColors, visualStyle, aspectRatio,
        generateImage: true, generateVideo: false, imageProvider, videoProvider,
      });
      if (plan.imagePrompt) setImagePrompt(plan.imagePrompt);
    } catch (e) {
      setError(e.message);
    }
  };

  const generateImageOnly = async () => {
    if (!imagePrompt.trim()) { setError('Enter or generate an image prompt first'); return; }
    setImageLoading(true);
    setError('');
    try {
      const result = await generateImage({
        prompt: imagePrompt.trim(),
        style: visualStyle,
        aspect_ratio: aspectRatio === '16:9' ? 'landscape' : aspectRatio === '1:1' ? 'square' : 'portrait',
        provider: imageProvider,
        brand_colors: brandColors,
        count: 2,
      });
      const images = result.images || [];
      setGeneratedImages(images);
      if (images.length > 0) setSelectedImage(images[0]);
    } catch (e) {
      setError(e.message);
    } finally {
      setImageLoading(false);
    }
  };

  const generateVideoScriptOnly = async () => {
    if (!topic.trim()) return;
    setError('');
    try {
      const plan = await generateContentPlan({
        topic: topic.trim(), audience, tone, contentType: 'text', brandColors, visualStyle, aspectRatio,
        generateImage: false, generateVideo: true, videoProvider, videoDuration: parseInt(videoDuration), videoStyle,
      });
      if (plan.videoScript) setVideoScript(plan.videoScript);
    } catch (e) {
      setError(e.message);
    }
  };

  const generateVideoOnly = async () => {
    setVideoLoading(true);
    setError('');
    try {
      const result = await startVideoGeneration({
        topic: topic.trim(),
        script: videoScript || '',
        duration: parseInt(videoDuration),
        voice: 'none',
        captions: false,
        style: videoStyle,
      });
      setVideoJobId(result.job_id);
      const fakeStepIdx = steps.length;
      setSteps(prev => [...prev, { label: 'Rendering video...', status: 'active', detail: 'This may take a few minutes' }]);
      startVideoPolling(result.job_id, fakeStepIdx);
    } catch (e) {
      setError(e.message);
      setVideoLoading(false);
    }
  };

  const saveDraft = async () => {
    setBusy(true);
    try {
      const mediaPayload = {};
      if (selectedImage) {
        mediaPayload.image = {
          enabled: true,
          provider: imageProvider,
          prompt: imagePrompt,
          filename: selectedImage.filename,
          url: selectedImage.url || `/api/media/file/${selectedImage.filename}`,
          mime_type: 'image/png',
          alt_text: altText,
          style: visualStyle,
          aspect_ratio: aspectRatio,
          status: 'generated',
        };
      }
      if (videoResult) {
        mediaPayload.video = {
          enabled: true,
          provider: videoProvider,
          prompt: topic,
          script: videoScript,
          filename: videoResult.filename,
          url: videoResult.url || `/api/media/file/${videoResult.filename}`,
          mime_type: 'video/mp4',
          duration: parseInt(videoDuration),
          style: videoStyle,
          status: 'generated',
          job_id: videoJobId || '',
        };
      }
      const savePayload = {
        title: suggestedTitle || topic,
        topic,
        audience: audience || 'general',
        tone,
        content: postText,
        hashtags,
        cta,
        content_type: contentType,
        media: Object.keys(mediaPayload).length > 0 ? mediaPayload : null,
      };
      if (contentType === 'carousel' && carouselSlides.length > 0) {
        savePayload.carousel_slides = carouselSlides.map((s, i) => ({
          slide_num: s.slide_num || i + 1,
          heading: s.heading || '',
          body: s.body || '',
          bullets: s.bullets || [],
          visual_prompt: s.visual_prompt || s.visualPrompt || '',
          image_url: s.image_url || s.imageUrl || '',
        }));
      }
      if (contentType === 'poll' && pollQuestion.trim()) {
        savePayload.poll_question = pollQuestion.trim();
        savePayload.poll_options = (pollOptions || []).map((o) => String(o || '').trim()).filter(Boolean);
      }
      await savePost(savePayload);
      window.location.href = '/publish';
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };

  const handle = profileUrl ? profileUrl.replace(/https?:\/\/(www\.)?linkedin\.com\/in\/?/i, '').replace(/\/$/, '') : '';
  const wantImage = generateImg || contentType === 'image';
  const wantVideo = generateVid || contentType === 'video';

  return (
    <div className="animate-fade-in">
      {showProfileModal && (
        <ProfileSetupModal existing={profileUrl} onSave={saveProfile} onSkip={() => setShowProfileModal(false)} />
      )}

      {/* Profile badge */}
      {profileUrl && (
        <div className="flex justify-end mb-4">
          <div className="flex items-center gap-2 bg-studio-50 border border-studio-100 rounded-xl px-3 py-1.5 text-sm text-studio-700">
            <IconLinkedIn size={16} className="text-linkedin-600" />
            <span>Connected as <strong>in/{handle}</strong></span>
            <button onClick={() => setShowProfileModal(true)} className="text-studio-600 text-xs underline hover:text-studio-700">Change</button>
          </div>
        </div>
      )}
      {prefillNotice && (
        <div className="mb-4 text-sm text-studio-700 bg-studio-50 border border-studio-200 rounded-xl px-4 py-2">
          {prefillNotice}
        </div>
      )}

      {/* Content Type Selector */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">What do you want to create?</h2>
        <p className="text-sm text-gray-500 mb-4">Choose a content type and let AI handle the rest</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
          {CONTENT_TYPES.map((ct) => {
            const Icon = ct.icon;
            const isActive = contentType === ct.value;
            const colors = COLOR_MAP[ct.color];
            return (
              <button
                key={ct.value}
                onClick={() => {
                  setContentType(ct.value);
                  if (ct.value === 'image') setGenerateImg(true);
                  else if (ct.value === 'video') setGenerateVid(true);
                }}
                className={`content-type-card ${
                  isActive
                    ? `${colors.activeBorder} ${colors.activeBg} ring-2 ${colors.ring} shadow-sm`
                    : 'content-type-card-unselected'
                }`}
              >
                <div className={`w-9 h-9 rounded-lg ${colors.bg} flex items-center justify-center`}>
                  <Icon size={18} className={colors.text} />
                </div>
                <div className="text-xs font-semibold text-gray-900">{ct.label}</div>
                <div className="text-[10px] text-gray-500 leading-tight">{ct.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left column: Form (3/5) */}
        <div className="lg:col-span-3 space-y-4">

          {/* Core fields */}
          <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5 space-y-4">
            <Textarea label="Topic" value={topic} onChange={e => setTopic(e.target.value)} rows={3}
              placeholder='e.g., "AI agents for prior authorization on Google Cloud"' />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Target Audience" value={audience} onChange={e => setAudience(e.target.value)}
                placeholder="e.g., CTOs, cloud architects, healthcare" />
              <Select label="Tone" value={tone} onChange={e => setTone(e.target.value)} options={TONES} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Select label="Goal" value={goal} onChange={e => setGoal(e.target.value)} options={GOALS} />
              <Input label="Call-to-Action" value={ctaInput} onChange={e => setCtaInput(e.target.value)}
                placeholder="e.g., Comment below, DM me, Link in bio" />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Keywords" value={keywords} onChange={e => setKeywords(e.target.value)}
                placeholder="e.g., AI, Cloud, Healthcare" />
              <Input label="Writing Style" value={writingStyle} onChange={e => setWritingStyle(e.target.value)}
                placeholder="e.g., Simon Sinek, concise, data-heavy" />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Select label="Visual Style" value={visualStyle} onChange={e => setVisualStyle(e.target.value)} options={VISUAL_STYLES} />
              <Select label="Aspect Ratio" value={aspectRatio} onChange={e => setAspectRatio(e.target.value)} options={ASPECT_RATIOS} />
              <Input label="Brand Colors" value={brandColors} onChange={e => setBrandColors(e.target.value)}
                placeholder="#0A66C2, #FFFFFF" />
            </div>
          </div>

          {/* Media enhancements */}
          <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Media Enhancements</h3>
            <div className="space-y-3">
              {/* Image toggle */}
              <div className={`border rounded-xl p-4 transition-all ${wantImage ? 'border-purple-200 bg-purple-50/50' : 'border-gray-100'}`}>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" checked={wantImage}
                    onChange={e => {
                      setGenerateImg(e.target.checked);
                      if (contentType === 'image' && !e.target.checked) setContentType('text');
                    }}
                    className="rounded border-gray-300 text-studio-600 focus:ring-studio-500 w-5 h-5" />
                  <div>
                    <span className="font-semibold text-sm text-gray-900">Add AI Image</span>
                    <span className="text-xs text-gray-500 ml-2">xAI visual enhancement</span>
                  </div>
                </label>

                {wantImage && (
                  <div className="mt-4 space-y-3 pl-8">
                    <Select label="Image Provider" value={imageProvider} onChange={e => setImageProvider(e.target.value)} options={IMAGE_PROVIDERS} />
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">Image Prompt</label>
                      <textarea value={imagePrompt} onChange={e => setImagePrompt(e.target.value)} rows={3}
                        placeholder="Leave blank to auto-generate from topic..."
                        className="input-field" />
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={generateImagePromptOnly} variant="outline" size="sm" disabled={!topic.trim() || busy}>
                        Generate Prompt with xAI
                      </Button>
                      <Button onClick={generateImageOnly} variant="outline" size="sm" disabled={!imagePrompt.trim() || imageLoading} loading={imageLoading}>
                        Generate Image
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Video toggle */}
              <div className={`border rounded-xl p-4 transition-all ${wantVideo ? 'border-red-200 bg-red-50/50' : 'border-gray-100'}`}>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" checked={wantVideo}
                    onChange={e => {
                      setGenerateVid(e.target.checked);
                      if (contentType === 'video' && !e.target.checked) setContentType('text');
                    }}
                    className="rounded border-gray-300 text-studio-600 focus:ring-studio-500 w-5 h-5" />
                  <div>
                    <span className="font-semibold text-sm text-gray-900">Add AI Video</span>
                    <span className="text-xs text-gray-500 ml-2">xAI video enhancement</span>
                  </div>
                </label>

                {wantVideo && (
                  <div className="mt-4 space-y-3 pl-8">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <Select label="Video Provider" value={videoProvider} onChange={e => setVideoProvider(e.target.value)} options={VIDEO_PROVIDERS} />
                      <Select label="Duration" value={videoDuration} onChange={e => setVideoDuration(e.target.value)} options={VIDEO_DURATIONS} />
                      <Select label="Video Style" value={videoStyle} onChange={e => setVideoStyle(e.target.value)} options={VIDEO_STYLES} />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">Video Script</label>
                      <textarea value={videoScript} onChange={e => setVideoScript(e.target.value)} rows={3}
                        placeholder="Leave blank to auto-generate from topic..."
                        className="input-field" />
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={generateVideoScriptOnly} variant="outline" size="sm" disabled={!topic.trim() || busy}>
                        Generate Script with xAI
                      </Button>
                      <Button onClick={generateVideoOnly} variant="outline" size="sm" disabled={videoLoading} loading={videoLoading}>
                        Generate Video
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Main generate button */}
          <button
            onClick={generateAll}
            disabled={busy || !topic.trim()}
            className="w-full py-3.5 rounded-2xl text-white font-semibold text-base
              bg-gradient-to-r from-studio-600 via-studio-500 to-linkedin-600
              hover:from-studio-700 hover:via-studio-600 hover:to-linkedin-700
              disabled:opacity-50 disabled:cursor-not-allowed
              shadow-lg hover:shadow-glow-lg transition-all duration-300
              flex items-center justify-center gap-2"
          >
            {busy ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                {aiCompleting ? 'xAI is completing missing fields...' : 'Generating...'}
              </>
            ) : (
              <>
                <IconSparkles size={20} />
                Generate Content
              </>
            )}
          </button>

          {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3">{error}</div>}

          {steps.length > 0 && <GenerationProgress steps={steps} />}

          {/* Generated images gallery */}
          {generatedImages.length > 0 && (
            <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Generated Images</h3>
              <div className="grid grid-cols-2 gap-3">
                {generatedImages.map((img, i) => (
                  <div key={i} onClick={() => setSelectedImage(img)}
                    className={`relative rounded-xl overflow-hidden border-2 cursor-pointer transition-all ${
                      selectedImage?.filename === img.filename
                        ? 'border-studio-600 shadow-glow ring-2 ring-studio-200'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}>
                    <img src={getMediaFileUrl(img.filename)} alt={`Generated ${i + 1}`} className="w-full h-auto" />
                    {selectedImage?.filename === img.filename && (
                      <div className="absolute top-2 right-2 bg-studio-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">✓</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Video result */}
          {videoResult && (
            <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Generated Video</h3>
              <video controls className="w-full rounded-xl border border-gray-200"
                src={getMediaFileUrl(videoResult.filename)} />
            </div>
          )}

          {/* Editable generated content */}
          {postText && (
            <div className="bg-white rounded-2xl shadow-card border border-gray-100 p-5 space-y-4">
              <div className="flex items-center gap-2">
                <IconSparkles size={18} className="text-studio-600" />
                <h3 className="text-sm font-semibold text-gray-900">Generated Post</h3>
                <span className="text-xs text-gray-400">Edit before saving</span>
              </div>
              <Input label="Title" value={suggestedTitle} onChange={e => setSuggestedTitle(e.target.value)} />
              <Textarea label="Content" value={postText} onChange={e => setPostText(e.target.value)} rows={8} />
              <Input label="Hashtags" value={hashtags.join(' ')} onChange={e => setHashtags(e.target.value.split(' ').filter(Boolean))} />
              <Input label="CTA" value={cta} onChange={e => setCta(e.target.value)} />
              {altText && <Input label="Alt Text" value={altText} onChange={e => setAltText(e.target.value)} />}

              {carouselSlides.length > 0 && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Carousel Slides</label>
                  <div className="space-y-2">
                    {carouselSlides.map((slide, i) => (
                      <div key={i} className="p-3 bg-gray-50 border border-gray-100 rounded-xl text-sm">
                        <div className="font-semibold">Slide {slide.slide_num || i + 1}: {slide.heading}</div>
                        {slide.body && <div className="text-gray-600 mt-1">{slide.body}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {pollQuestion && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Poll</label>
                  <div className="p-3 bg-gray-50 border border-gray-100 rounded-xl text-sm">
                    <div className="font-semibold mb-2">{pollQuestion}</div>
                    {pollOptions.map((opt, i) => (
                      <div key={i} className="bg-studio-50 border border-studio-100 rounded-lg px-3 py-1.5 mb-1 text-xs">{opt}</div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <Button onClick={saveDraft} disabled={busy} variant="primary" className="flex-1">Save as Draft</Button>
                <Button onClick={generateAll} disabled={busy} variant="outline">Regenerate</Button>
              </div>
            </div>
          )}
        </div>

        {/* Right column: Preview (2/5) */}
        <div className="lg:col-span-2 hidden lg:block">
          <div className="sticky top-20">
            <LinkedInPreview
              title={suggestedTitle}
              content={postText || (topic ? `Topic: ${topic}` : '')}
              hashtags={hashtags}
              cta={cta}
              profileUrl={profileUrl}
              image={selectedImage}
              video={videoResult}
              poll={pollQuestion ? { question: pollQuestion, options: pollOptions } : null}
              imageLoading={imageLoading}
              videoLoading={videoLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CreatePage() {
  return (
    <Suspense fallback={<div className="flex justify-center py-12"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-studio-600"></div></div>}>
      <CreatePageContent />
    </Suspense>
  );
}
