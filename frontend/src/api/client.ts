import axios from 'axios';

// Get base URL from environment or localStorage override, fallback to /api
export const getApiBaseUrl = (): string => {
  const localOverride = localStorage.getItem('crypto_api_base_url');
  if (localOverride) return localOverride;
  return import.meta.env.VITE_API_BASE_URL || '/api';
};

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Update base URL dynamically when settings change
export const setApiBaseUrl = (url: string) => {
  localStorage.setItem('crypto_api_base_url', url);
  api.defaults.baseURL = url;
};

// Endpoints
export const endpoints = {
  health: () => api.get('/health'),
  getStats: () => api.get('/stats'),
  createTransfer: (formData: FormData) =>
    api.post('/transfers', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getTransferStatus: (id: string) => api.get(`/transfers/${id}/status`),
  scanQR: (id: string, qrPayload?: any) =>
    api.post(`/transfers/${id}/scan`, { qr_payload: qrPayload }),
  verifyPassword: (id: string, password: string, token: string) =>
    api.post(
      `/transfers/${id}/password`,
      { password },
      { headers: { Authorization: `Bearer ${token}` } }
    ),
  checkKeyReveal: (id: string, token: string) =>
    api.post(`/transfers/${id}/key-reveal`, {}, { headers: { Authorization: `Bearer ${token}` } }),
  enrollEye: (id: string, frames: string[], token: string) =>
    api.post(
      `/transfers/${id}/eye/enroll`,
      { frames },
      { headers: { Authorization: `Bearer ${token}` } }
    ),
  verifyEye: (id: string, frames: string[], opennessHistory: number[], token: string) =>
    api.post(
      `/transfers/${id}/eye/verify`,
      { frames, openness_history: opennessHistory },
      { headers: { Authorization: `Bearer ${token}` } }
    ),
  decryptFile: (id: string, password: string, token: string) =>
    api.post(
      `/transfers/${id}/decrypt`,
      { password },
      { headers: { Authorization: `Bearer ${token}` } }
    ),
  downloadDecryptedCsv: (id: string, password: string, token: string) =>
    api.post(
      `/transfers/${id}/download-csv`,
      { password },
      {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      }
    ),
  downloadDecryptedExcel: (id: string, password: string, token: string) =>
    api.post(
      `/transfers/${id}/download-excel`,
      { password },
      {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      }
    ),
  runBenchmark: (formData?: FormData) =>
    api.post('/benchmark', formData || {}, {
      headers: formData ? { 'Content-Type': 'multipart/form-data' } : {},
    }),
  getBenchmarkHistory: () => api.get('/benchmark/history'),
  getAuditLogs: (limit = 50, transferId?: string) =>
    api.get('/audit-logs', { params: { limit, transfer_id: transferId } }),
};
