import React, { useState, useEffect, useRef } from 'react';
import { api } from './services/api';
import { Task } from './types';
import { TaskInput } from './components/TaskInput';
import { ExecutionTimeline } from './components/ExecutionTimeline';
import { ApprovalCard } from './components/ApprovalCard';
import { FinalResult } from './components/FinalResult';
import { EvidenceGallery } from './components/EvidenceGallery';
import {
  Bot,
  ExternalLink,
  Activity,
  Layers,
  ShieldCheck,
} from 'lucide-react';

export const App: React.FC = () => {
  // Remove trailing slash from VITE_API_URL.
  // If no VITE_API_URL is provided, use the current deployed domain.
  const API_BASE = (
    import.meta.env.VITE_API_URL || window.location.origin
  ).replace(/\/+$/, '');

  const INVOICE_PORTAL_URL = `${API_BASE}/sandbox/invoice-portal`;
  const BILLING_PORTAL_URL = `${API_BASE}/sandbox/billing-portal`;

  const [currentTask, setCurrentTask] = useState<Task | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isApprovalProcessing, setIsApprovalProcessing] = useState(false);
  const pollIntervalRef = useRef<any>(null);

  // Poll for task execution updates
  useEffect(() => {
    if (
      !currentTask ||
      ['COMPLETED', 'FAILED', 'CANCELLED'].includes(currentTask.status)
    ) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const updated = await api.getTask(currentTask.id);
        setCurrentTask(updated);

        if (
          ['COMPLETED', 'FAILED', 'CANCELLED'].includes(updated.status)
        ) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      } catch (err) {
        console.error('Error polling task updates:', err);
      }
    }, 1500);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [currentTask?.id, currentTask?.status]);

  const handleStartTask = async (
    prompt: string,
    simulateFailure: boolean
  ) => {
    try {
      setIsSubmitting(true);

      const newTask = await api.createTask(
        prompt,
        simulateFailure
      );

      setCurrentTask(newTask);
    } catch (err) {
      console.error('Error starting task:', err);
      alert(
        'Failed to start task. Please ensure the backend is running.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async (notes: string) => {
    if (!currentTask) return;

    try {
      setIsApprovalProcessing(true);

      await api.approveTask(currentTask.id, notes);

      const updated = await api.getTask(currentTask.id);
      setCurrentTask(updated);
    } catch (err) {
      console.error('Error approving task:', err);
      alert('Approval submission failed.');
    } finally {
      setIsApprovalProcessing(false);
    }
  };

  const handleReject = async (notes: string) => {
    if (!currentTask) return;

    try {
      setIsApprovalProcessing(true);

      await api.rejectTask(currentTask.id, notes);

      const updated = await api.getTask(currentTask.id);
      setCurrentTask(updated);
    } catch (err) {
      console.error('Error rejecting task:', err);
      alert('Rejection submission failed.');
    } finally {
      setIsApprovalProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">

      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-3.5 flex items-center justify-between">

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Bot className="w-5 h-5 text-white" />
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-bold text-base tracking-tight text-white">
                  Autonomous AI Task Worker
                </h1>

                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  v1.0
                </span>
              </div>

              <p className="text-xs text-slate-400">
                Agentic Browser Automation & Ledger Reconciliation
              </p>
            </div>
          </div>

          {/* Quick Sandbox Navigation */}
          <div className="flex items-center gap-3 text-xs">

            <a
              href={INVOICE_PORTAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/70 transition"
            >
              <span>Invoice Portal</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>

            <a
              href={BILLING_PORTAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/70 transition"
            >
              <span>Billing System</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>

          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="max-w-6xl mx-auto px-4 py-8 flex-1 w-full space-y-6">

        {/* Architecture Badges */}
        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            <span>LangGraph Deterministic Core</span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>Playwright Live Automation</span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800">
            <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
            <span>Human-in-the-Loop Approval</span>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Independent Verification</span>
          </div>

        </div>

        {/* Task Dispatcher */}
        <TaskInput
          onSubmit={handleStartTask}
          isLoading={
            isSubmitting || currentTask?.status === 'RUNNING'
          }
        />

        {/* Human in the loop Approval Card */}
        {currentTask &&
          currentTask.status === 'AWAITING_APPROVAL' && (
            <ApprovalCard
              payload={currentTask.extracted_data}
              onApprove={handleApprove}
              onReject={handleReject}
              isProcessing={isApprovalProcessing}
            />
          )}

        {/* Final Result Card */}
        {currentTask &&
          ['COMPLETED', 'FAILED', 'CANCELLED'].includes(
            currentTask.status
          ) && <FinalResult task={currentTask} />}

        {/* Execution Timeline */}
        {currentTask && (
          <ExecutionTimeline
            steps={currentTask.steps}
            currentStatus={currentTask.status}
          />
        )}

        {/* Evidence Gallery */}
        {currentTask &&
          currentTask.evidence_items &&
          currentTask.evidence_items.length > 0 && (
            <EvidenceGallery
              items={currentTask.evidence_items}
            />
          )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6 text-center text-xs text-slate-500">
        Autonomous AI Task Worker &bull; Production Agentic Prototype
        &bull; FastAPI + LangGraph + Playwright + React
      </footer>

    </div>
  );
};

export default App;