import React from 'react';
import { ExecutionStep } from '../types';
import { CheckCircle2, Clock, AlertTriangle, RefreshCw, XCircle } from 'lucide-react';

interface ExecutionTimelineProps {
  steps: ExecutionStep[];
  currentStatus: string;
}

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({ steps, currentStatus }) => {
  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />;
      case 'retrying':
        return <RefreshCw className="w-5 h-5 text-amber-400 animate-spin flex-shrink-0" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-400 flex-shrink-0" />;
      case 'pending':
      case 'awaiting_approval':
        return <Clock className="w-5 h-5 text-indigo-400 animate-pulse flex-shrink-0" />;
      default:
        return <div className="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />;
    }
  };

  const formatActionTitle = (action: string) => {
    return action
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
  };

  return (
    <div className="bg-slate-800/90 border border-slate-700/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-700/60">
        <div>
          <h2 className="text-base font-semibold text-white">Execution Timeline & Audit Log</h2>
          <p className="text-xs text-slate-400">Deterministic sequence of browser tool interactions</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-slate-900 border border-slate-700 text-slate-300">
            {steps.length} Steps Executed
          </span>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider ${
            currentStatus === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
            currentStatus === 'AWAITING_APPROVAL' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse' :
            currentStatus === 'FAILED' ? 'bg-red-500/20 text-red-300 border border-red-500/40' :
            'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
          }`}>
            {currentStatus}
          </span>
        </div>
      </div>

      {steps.length === 0 ? (
        <div className="py-12 text-center text-slate-500">
          <p className="text-sm">Awaiting task dispatch...</p>
        </div>
      ) : (
        <div className="space-y-4 relative before:absolute before:inset-0 before:left-2.5 before:w-0.5 before:bg-slate-700/50">
          {steps.map((step, index) => {
            const obsText = typeof step.observation === 'object' && step.observation?.details
              ? step.observation.details
              : typeof step.observation === 'string'
              ? step.observation
              : JSON.stringify(step.observation || {});

            return (
              <div key={step.id || index} className="relative flex items-start gap-4 pl-8 group">
                <div className="absolute left-0 top-0.5 bg-slate-900 ring-4 ring-slate-800 rounded-full">
                  {getStatusIcon(step.status)}
                </div>

                <div className="flex-1 bg-slate-900/60 border border-slate-700/70 rounded-xl p-3.5 hover:border-slate-600 transition">
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-indigo-400 font-bold">
                        Step {step.step_number}
                      </span>
                      <h4 className="text-sm font-semibold text-slate-100">
                        {formatActionTitle(step.action)}
                      </h4>
                      {step.retry_count > 0 && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          Retry #{step.retry_count}
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono">
                      {step.started_at ? new Date(step.started_at).toLocaleTimeString() : ''}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed font-sans">
                    {obsText}
                  </p>

                  {step.error && (
                    <div className="mt-2 p-2 bg-red-950/40 border border-red-800/50 rounded-lg text-xs text-red-300 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                      <span>{step.error}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
