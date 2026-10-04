import axios from 'axios';
import { Task, ExecutionStep, EvidenceItem } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '';

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  async getHealth() {
    const res = await client.get('/api/health');
    return res.data;
  },

  async createTask(userTask: string, simulateSaveFailure: boolean = false): Promise<Task> {
    const res = await client.post('/api/tasks', {
      user_task: userTask,
      simulate_save_failure: simulateSaveFailure,
    });
    return res.data;
  },

  async getTask(taskId: string): Promise<Task> {
    const res = await client.get(`/api/tasks/${taskId}`);
    return res.data;
  },

  async getExecution(taskId: string): Promise<{
    task_id: string;
    status: string;
    current_step: number;
    total_steps: number;
    steps: ExecutionStep[];
    extracted_data?: any;
    verification_result?: any;
  }> {
    const res = await client.get(`/api/tasks/${taskId}/execution`);
    return res.data;
  },

  async getEvidence(taskId: string): Promise<{ task_id: string; evidence_items: EvidenceItem[] }> {
    const res = await client.get(`/api/tasks/${taskId}/evidence`);
    return res.data;
  },

  async approveTask(taskId: string, notes: string = ''): Promise<any> {
    const res = await client.post(`/api/tasks/${taskId}/approve`, { notes });
    return res.data;
  },

  async rejectTask(taskId: string, notes: string = ''): Promise<any> {
    const res = await client.post(`/api/tasks/${taskId}/reject`, { notes });
    return res.data;
  },
};
