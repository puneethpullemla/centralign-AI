import React, { useState } from 'react';
import { Play, Sparkles, AlertTriangle, ArrowRight } from 'lucide-react';

interface TaskInputProps {
  onSubmit: (prompt: string, simulateFailure: boolean) => void;
  isLoading: boolean;
}

export const TaskInput: React.FC<TaskInputProps> = ({ onSubmit, isLoading }) => {
  const [prompt, setPrompt] = useState('');
  const [simulateFailure, setSimulateFailure] = useState(false);

  const presets = [
    {
      title: 'Acme Invoice (Assignment Objective)',
      text: 'Find the latest invoice from Acme, extract the invoice amount and due date, enter the information into our internal billing system, and tell me once it is completed.',
    },
    {
      title: 'Globex Invoice (Generalization Demo)',
      text: 'Find the latest invoice from Globex, extract the invoice amount and due date, enter the information into our internal billing system, and tell me once it is completed.',
    },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;
    onSubmit(prompt.trim(), simulateFailure);
  };

  return (
    <div className="bg-slate-800/90 border border-slate-700/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Describe Your Task</h2>
            <p className="text-xs text-slate-400">Natural language instruction for the autonomous agent</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isLoading}
            rows={3}
            placeholder="Describe what you want the AI worker to do..."
            className="w-full bg-slate-900/80 border border-slate-700 rounded-xl p-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition disabled:opacity-50"
          />
        </div>

        {/* Quick Presets */}
        <div>
          <span className="text-xs font-medium text-slate-400 block mb-2">Preset Scenarios:</span>
          <div className="flex flex-wrap gap-2">
            {presets.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setPrompt(preset.text)}
                disabled={isLoading}
                className="text-xs px-3 py-1.5 rounded-lg bg-slate-900/60 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition flex items-center gap-1.5"
              >
                <span>{preset.title}</span>
                <ArrowRight className="w-3 h-3 text-slate-500" />
              </button>
            ))}
          </div>
        </div>

        {/* Simulation Option */}
        <div className="flex items-center justify-between p-3 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <div>
              <span className="text-xs font-semibold text-slate-200">Simulate Intermittent Billing Save Error</span>
              <p className="text-[11px] text-slate-400">Exercises agent observation, duplicate check, and safe retry recovery</p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={simulateFailure}
              onChange={(e) => setSimulateFailure(e.target.checked)}
              disabled={isLoading}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-500"></div>
          </label>
        </div>

        {/* Action Button */}
        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={isLoading || !prompt.trim()}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-medium text-sm transition shadow-lg shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Worker Running...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Start Autonomous Task</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
