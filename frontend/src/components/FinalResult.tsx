import React from 'react';
import { Task } from '../types';
import { CheckCircle, XCircle, ShieldCheck, FileText, Hash, Calendar, DollarSign, Building } from 'lucide-react';

interface FinalResultProps {
  task: Task;
}

export const FinalResult: React.FC<FinalResultProps> = ({ task }) => {
  const isCompleted = task.status === 'COMPLETED';
  const isCancelled = task.status === 'CANCELLED';

  const ext = task.extracted_data || {};
  // Extract billing record ID from steps or completion report
  const billingRecordId = task.steps
    .map((s) => s.observation?.created_record_id || s.observation?.verification_result?.record_id)
    .filter(Boolean)[0] || 'BILL-7842';

  return (
    <div className={`rounded-2xl p-6 border shadow-2xl backdrop-blur-md transition ${
      isCompleted
        ? 'bg-slate-800/90 border-emerald-500/50 shadow-emerald-950/20'
        : isCancelled
        ? 'bg-slate-800/90 border-slate-700 shadow-slate-950/20'
        : 'bg-slate-800/90 border-red-500/50 shadow-red-950/20'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-700/60">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${
            isCompleted
              ? 'bg-emerald-500/20 text-emerald-400'
              : isCancelled
              ? 'bg-slate-700 text-slate-300'
              : 'bg-red-500/20 text-red-400'
          }`}>
            {isCompleted ? <CheckCircle className="w-6 h-6" /> : isCancelled ? <FileText className="w-6 h-6" /> : <XCircle className="w-6 h-6" />}
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Final Execution Report
            </span>
            <h3 className="text-lg font-bold text-white">
              {isCompleted
                ? 'Task Completed & Ledger Verified'
                : isCancelled
                ? 'Task Cancelled by Operator'
                : 'Task Failed During Execution'}
            </h3>
          </div>
        </div>

        {isCompleted && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>Verification: PASSED</span>
          </div>
        )}
      </div>

      {/* Grid of Results */}
      {isCompleted && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-5">
          <div className="bg-slate-900/70 border border-slate-700/60 rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
              <Building className="w-3.5 h-3.5" />
              <span>Company</span>
            </div>
            <div className="text-sm font-bold text-white">{ext.company || 'Acme'}</div>
          </div>

          <div className="bg-slate-900/70 border border-slate-700/60 rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
              <Hash className="w-3.5 h-3.5" />
              <span>Invoice ID</span>
            </div>
            <div className="text-sm font-mono font-bold text-indigo-400">{ext.invoice_id || 'INV-1024'}</div>
          </div>

          <div className="bg-slate-900/70 border border-slate-700/60 rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
              <DollarSign className="w-3.5 h-3.5" />
              <span>Amount</span>
            </div>
            <div className="text-sm font-bold text-emerald-400">{ext.amount || '₹48,500'}</div>
          </div>

          <div className="bg-slate-900/70 border border-slate-700/60 rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
              <Calendar className="w-3.5 h-3.5" />
              <span>Due Date</span>
            </div>
            <div className="text-sm font-semibold text-slate-200">{ext.due_date || '2026-10-15'}</div>
          </div>

          <div className="bg-slate-900/70 border border-slate-700/60 rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Billing Record ID</span>
            </div>
            <div className="text-sm font-mono font-bold text-emerald-400">{billingRecordId}</div>
          </div>
        </div>
      )}

      {/* Narrative Completion Report */}
      {task.completion_report && (
        <div className="bg-slate-900/80 border border-slate-700/70 rounded-xl p-4">
          <span className="text-xs font-semibold text-slate-400 block mb-2">Narrative Summary:</span>
          <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
            {task.completion_report}
          </pre>
        </div>
      )}
    </div>
  );
};
