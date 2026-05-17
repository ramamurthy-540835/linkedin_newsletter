'use client';

import { IconSearch, IconEdit, IconSparkles, IconSend, IconCheckCircle } from './icons';

const STAGES = [
  { key: 'research', Icon: IconSearch, label: 'Research' },
  { key: 'writer', Icon: IconEdit, label: 'Write' },
  { key: 'hashtags', Icon: IconSparkles, label: 'Hashtags' },
  { key: 'cta', Icon: IconSend, label: 'CTA' },
  { key: 'complete', Icon: IconCheckCircle, label: 'Done' }
];

export default function ProgressStream({ progress }) {
  const getStageStatus = (stageKey) => {
    const found = progress.find(p => p.stage === stageKey);
    return found?.status || 'pending';
  };

  const getStageMessage = (stageKey) => {
    const found = progress.find(p => p.stage === stageKey);
    return found?.message || '';
  };

  const getStageTiming = (stageKey) => {
    const found = progress.find(p => p.stage === stageKey);
    return found?.timing || '';
  };

  const completedCount = progress.filter(p => p.status === 'done').length;
  const activeStage = progress.find(p => p.status === 'starting');

  return (
    <div className="bg-gradient-to-br from-linkedin-50 to-blue-50 border border-linkedin-200 rounded-lg p-6">
      <div className="font-bold text-lg mb-6 text-linkedin-700">Generation Progress</div>

      <div className="flex items-center justify-between gap-2 mb-8 relative">
        {STAGES.map((stage, idx) => {
          const status = getStageStatus(stage.key);
          const isCompleted = status === 'done';
          const isActive = status === 'starting';
          const isFailed = status === 'failed';

          return (
            <div key={stage.key} className="flex flex-col items-center flex-1 relative">
              <div className={`w-14 h-14 rounded-full flex items-center justify-center text-2xl font-bold transition mb-2 ${
                isCompleted ? 'bg-green-100 text-green-700 ring-2 ring-green-300' :
                isActive ? 'bg-yellow-100 text-yellow-700 ring-2 ring-yellow-300 animate-pulse' :
                isFailed ? 'bg-red-100 text-red-700 ring-2 ring-red-300' :
                'bg-gray-200 text-gray-500'
              }`}>
                {isCompleted ? <IconCheckCircle size={28} className="text-green-600" /> :
                 isFailed ? <span>X</span> :
                 <stage.Icon size={24} />}
              </div>

              <div className="text-sm font-bold text-center text-gray-900">{stage.label}</div>

              {idx < STAGES.length - 1 && (
                <div className={`absolute h-1 w-full top-7 left-1/2 ${isCompleted ? 'bg-green-300' : 'bg-gray-300'}`} />
              )}
            </div>
          );
        })}
      </div>

      <div className="border-t border-linkedin-200 pt-6">
        <div className="font-bold text-sm text-linkedin-700 mb-4">Stage Details</div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {STAGES.map((stage) => {
            const status = getStageStatus(stage.key);
            const message = getStageMessage(stage.key);
            const timing = getStageTiming(stage.key);
            const isCompleted = status === 'done';
            const isActive = status === 'starting';

            return (
              <div
                key={stage.key}
                className={`p-3 rounded-lg border text-xs ${
                  isCompleted ? 'bg-green-50 border-green-200' :
                  isActive ? 'bg-yellow-50 border-yellow-200' :
                  'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-center gap-1 mb-2">
                  <div className={`w-2 h-2 rounded-full ${
                    isCompleted ? 'bg-green-500' :
                    isActive ? 'bg-yellow-500 animate-pulse' :
                    'bg-gray-400'
                  }`} />
                  <span className="font-bold capitalize">{status}</span>
                </div>

                {message && (
                  <div className="text-gray-700 mb-2 line-clamp-2">{message}</div>
                )}

                {timing && (
                  <div className="font-mono text-gray-600">{timing}</div>
                )}

                {status === 'pending' && (
                  <div className="text-gray-500 italic">Waiting...</div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-linkedin-200">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-bold text-gray-700">Overall Progress</span>
          <span className="text-sm font-bold text-gray-700">{completedCount}/{STAGES.length}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className="bg-linkedin-600 h-3 rounded-full transition-all duration-300"
            style={{
              width: `${(completedCount / STAGES.length) * 100}%`
            }}
          />
        </div>
      </div>

      {getStageStatus('complete') === 'success' && (
        <div className="mt-4 p-3 bg-green-100 border border-green-300 rounded-lg">
          <div className="text-sm font-bold text-green-700">Post generated successfully!</div>
        </div>
      )}

      {progress.some(p => p.status === 'failed') && (
        <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded-lg">
          <div className="text-sm font-bold text-red-700">Generation failed</div>
          {progress.find(p => p.status === 'failed')?.message && (
            <div className="text-xs text-red-600 mt-1">
              {progress.find(p => p.status === 'failed')?.message}
            </div>
          )}
        </div>
      )}

      {activeStage && (
        <div className="mt-4 p-3 bg-linkedin-50 border border-linkedin-200 rounded-lg">
          <div className="text-sm font-bold text-linkedin-700">Currently processing...</div>
          <div className="text-xs text-linkedin-600 mt-1">{activeStage.message}</div>
        </div>
      )}
    </div>
  );
}
