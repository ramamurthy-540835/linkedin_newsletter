'use client';
import { useState, useEffect, useRef } from 'react';
import Card from '@/components/Card';
import Button from '@/components/Button';
import Select from '@/components/Select';
import Textarea from '@/components/Textarea';
import Input from '@/components/Input';
import { generateVideoScript, startVideoGeneration, getMediaJobStatus, getMediaFileUrl } from '@/lib/api';

const SCRIPT_STYLES = [
  { value: 'corporate', label: 'Corporate' },
  { value: 'tech_demo', label: 'Tech Demo' },
  { value: 'storytelling', label: 'Storytelling' },
  { value: 'explainer', label: 'Explainer' },
  { value: 'social_media', label: 'Social Media' },
];

const DURATIONS = [
  { value: '15', label: '15 seconds' },
  { value: '30', label: '30 seconds' },
  { value: '60', label: '60 seconds' },
];

const VOICES = [
  { value: 'none', label: 'No Voice' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
];

const STAGE_LABELS = {
  script: 'Script',
  scenes: 'Scenes',
  rendering: 'Rendering',
  final: 'Finalizing',
};

function VideoProgress({ stages }) {
  if (!stages) return null;
  const entries = Object.entries(STAGE_LABELS);

  return (
    <div className="flex items-center gap-2 mt-4">
      {entries.map(([key, label], i) => {
        const status = stages[key] || 'pending';
        const colors = {
          pending: 'bg-gray-200 text-gray-500',
          in_progress: 'bg-linkedin-100 text-linkedin-700 animate-pulse',
          completed: 'bg-green-100 text-green-700',
          failed: 'bg-red-100 text-red-700',
        };

        return (
          <div key={key} className="flex items-center gap-1">
            <div className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${colors[status] || colors.pending}`}>
              {status === 'completed' && <span className="mr-1">&#10003;</span>}
              {status === 'in_progress' && <span className="mr-1">&#9679;</span>}
              {label}
            </div>
            {i < entries.length - 1 && <div className="w-4 h-px bg-gray-300" />}
          </div>
        );
      })}
    </div>
  );
}

export default function VideoGeneratorPanel({ onAttach }) {
  const [topic, setTopic] = useState('');
  const [script, setScript] = useState('');
  const [style, setStyle] = useState('corporate');
  const [duration, setDuration] = useState('30');
  const [voice, setVoice] = useState('none');
  const [captions, setCaptions] = useState(false);
  const [scriptLoading, setScriptLoading] = useState(false);
  const [videoLoading, setVideoLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [error, setError] = useState('');
  const pollRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const genScript = async () => {
    if (!topic.trim()) {
      setError('Please enter a video topic');
      return;
    }
    setScriptLoading(true);
    setError('');
    try {
      const result = await generateVideoScript({
        topic: topic.trim(),
        style,
        duration: parseInt(duration),
      });
      setScript(result.script || JSON.stringify(result, null, 2));
    } catch (e) {
      setError(e.message || 'Script generation failed');
    } finally {
      setScriptLoading(false);
    }
  };

  const genVideo = async () => {
    if (!topic.trim()) {
      setError('Please enter a video topic');
      return;
    }
    setVideoLoading(true);
    setError('');
    setVideoUrl(null);
    try {
      const result = await startVideoGeneration({
        topic: topic.trim(),
        script,
        duration: parseInt(duration),
        voice,
        captions,
        style,
      });
      setJobId(result.job_id);
      startPolling(result.job_id);
    } catch (e) {
      setError(e.message || 'Video generation failed');
      setVideoLoading(false);
    }
  };

  const startPolling = (id) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await getMediaJobStatus(id);
        setJobStatus(status);
        if (status.status === 'completed') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setVideoLoading(false);
          if (status.result?.filename) {
            setVideoUrl(getMediaFileUrl(status.result.filename));
          }
        } else if (status.status === 'failed') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setVideoLoading(false);
          setError(status.message || 'Video generation failed');
        }
      } catch {
        // keep polling
      }
    }, 5000);
  };

  const downloadVideo = () => {
    if (!videoUrl) return;
    const a = document.createElement('a');
    a.href = videoUrl;
    a.download = jobStatus?.result?.filename || 'video.mp4';
    a.click();
  };

  return (
    <div className="space-y-4">
      <Card title="Video Generation" subtitle="Create AI-generated video for your post">
        <div className="space-y-4">
          <Input
            label="Video Topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., AI transforming enterprise workflows"
          />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Select label="Script Style" value={style} onChange={(e) => setStyle(e.target.value)} options={SCRIPT_STYLES} />
            <Select label="Duration" value={duration} onChange={(e) => setDuration(e.target.value)} options={DURATIONS} />
            <Select label="Voice" value={voice} onChange={(e) => setVoice(e.target.value)} options={VOICES} />
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={captions}
                onChange={(e) => setCaptions(e.target.checked)}
                className="rounded border-gray-300 text-linkedin-600 focus:ring-linkedin-500"
              />
              <span className="text-sm text-gray-700">Enable captions</span>
            </label>
          </div>

          <div className="flex gap-3">
            <Button onClick={genScript} disabled={scriptLoading || !topic.trim()} variant="outline" loading={scriptLoading} className="flex-1">
              {scriptLoading ? 'Generating Script...' : 'Generate Script'}
            </Button>
            <Button onClick={genVideo} disabled={videoLoading || !topic.trim()} variant="primary" loading={videoLoading} className="flex-1">
              {videoLoading ? 'Generating Video...' : 'Generate Video'}
            </Button>
          </div>

          {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>}
        </div>
      </Card>

      {script && (
        <Card title="Video Script" subtitle="Edit before generating video">
          <Textarea
            value={script}
            onChange={(e) => setScript(e.target.value)}
            rows={6}
          />
        </Card>
      )}

      {videoLoading && jobStatus && (
        <Card title="Generation Progress" subtitle={jobStatus.message || 'Processing...'}>
          <VideoProgress stages={jobStatus.stages} />
          <div className="mt-3 text-sm text-gray-500">{jobStatus.message}</div>
        </Card>
      )}

      {videoUrl && (
        <Card title="Generated Video" subtitle="Preview and download your video">
          <video
            controls
            className="w-full rounded-xl border border-gray-200"
            src={videoUrl}
          >
            Your browser does not support video playback.
          </video>
          <div className="flex gap-3 mt-4">
            <Button onClick={downloadVideo} variant="outline" className="flex-1">
              Download
            </Button>
            {onAttach && (
              <Button onClick={() => onAttach(jobStatus?.result)} variant="primary" className="flex-1">
                Attach to Post
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
