import React, { useState } from 'react';
import { ShieldAlert, Check, X } from 'lucide-react';
import { ExtractedData } from '../types';

interface ApprovalCardProps {
  payload?: ExtractedData | null;
  onApprove: (notes: string) => void;
  onReject: (notes: string) => void;
  isProcessing: boolean;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  payload,
  onApprove,
  onReject,
  isProcessing,
}) => {
  const [notes, setNotes] = useState('');

  return (
    <div className="bg-gradient-to-r from-amber-950/40 via-slate-800/90 to-amber-950/40 border-2 border-amber-500/60 rounded-2xl p-6 shadow-2xl backdrop-blur-md animate-pulse-border">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 bg-amber-500/20 text-amber-400 rounded-xl">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div>
          <span className="text-xs font-bold text-amber-400 uppercase tracking-widest">
            Human-in-the-Loop Required
          </span>
          <h3 className="text-lg font-bold text-white">
            Confirm Record Submission to Billing Ledger
          </h3>
        </div>
      </div>

      <p className="text-xs text-slate-300 mb-5">
        The autonomous agent has retrieved and verified vendor invoice details from the Invoice Portal and is preparing to write a permanent ledger entry.
      </p>

      {/* Extracted Details Box */}
      <div className="bg-slate-900/90 border border-slate-700 rounded-xl p-4 mb-5 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <span className="text-[11px] text-slate-400 block mb-0.5">Company</span>
          <span className="text-sm font-semibold text-white">
            {payload?.company || 'N/A'}
          </span>
        </div>
        <div>
          <span className="text-[11px] text-slate-400 block mb-0.5">Invoice ID</span>
          <span className="text-sm font-mono font-bold text-indigo-400">
            {payload?.invoice_id || 'N/A'}
          </span>
        </div>
        <div>
          <span className="text-[11px] text-slate-400 block mb-0.5">Amount</span>
          <span className="text-sm font-bold text-emerald-400">
            {payload?.amount || 'N/A'}
          </span>
        </div>
        <div>
          <span className="text-[11px] text-slate-400 block mb-0.5">Due Date</span>
          <span className="text-sm font-semibold text-white">
            {payload?.due_date || 'N/A'}
          </span>
        </div>
      </div>

      {/* Optional Operator Notes */}
      <div className="mb-5">
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Operator approval notes (optional)..."
          disabled={isProcessing}
          className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-3">
        <button
          onClick={() => onReject(notes)}
          disabled={isProcessing}
          className="flex items-center gap-1.5 px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 font-medium text-xs rounded-xl transition disabled:opacity-50"
        >
          <X className="w-4 h-4" />
          <span>Reject & Halt</span>
        </button>
        <button
          onClick={() => onApprove(notes)}
          disabled={isProcessing}
          className="flex items-center gap-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-emerald-600/20 disabled:opacity-50"
        >
          <Check className="w-4 h-4" />
          <span>Approve & Write to Ledger</span>
        </button>
      </div>
    </div>
  );
};
