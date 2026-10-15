const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const BASE = `${apiBase}/api`;

export function wsUrl(token) {
  const wsBase = apiBase ? apiBase.replace(/^http/, 'ws') : window.location.origin.replace(/^http/, 'ws');
  return `${wsBase}/ws?token=${encodeURIComponent(token)}`;
}

function getToken() {
  return localStorage.getItem('scribe_token');
}

export function setToken(token) {
  if (token) localStorage.setItem('scribe_token', token);
  else localStorage.removeItem('scribe_token');
}

export function clearToken() {
  localStorage.removeItem('scribe_token');
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = getToken();
  const hadAuth = Boolean(token);
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }

  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/login') && !path.startsWith('/auth/signup')) {
      clearToken();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('scribe:unauthorized'));
      }
    }
    const error = new Error(data?.detail || data?.message || response.statusText);
    error.code = data?.code || `HTTP_${response.status}`;
    error.status = response.status;
    throw error;
  }

  return data;
}

export const api = {
  status: async () => request('/status'),
  signup: async ({ email, password }) =>
    request('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: async ({ email, password }) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: async () => request('/auth/me'),
  logout: () => {
    clearToken();
  },
  sync: async () => request('/integrations/granola/sync', { method: 'POST' }),
  captures: async () => request('/integrations/recall/captures'),
  createCapture: async (payload) =>
    request('/integrations/recall/captures', { method: 'POST', body: JSON.stringify(payload) }),
  cancelCapture: async (id) =>
    request(`/integrations/recall/captures/${id}`, { method: 'DELETE' }),
  calendars: async () => request('/integrations/recall/calendars'),
  createCalendar: async (payload) =>
    request('/integrations/recall/calendars', { method: 'POST', body: JSON.stringify(payload) }),
  calendarEvents: async (id, updatedSince) =>
    request(`/integrations/recall/calendars/${id}/events${updatedSince ? `?updated_at_gte=${encodeURIComponent(updatedSince)}` : ''}`),
  scheduleCalendarEvent: async (connectionId, eventId, payload) =>
    request(`/integrations/recall/calendars/${connectionId}/events/${eventId}/schedule`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deleteCalendar: async (id) =>
    request(`/integrations/recall/calendars/${id}`, { method: 'DELETE' }),
  notes: async () => request('/meetings'),
  note: async (id) => request(`/meetings/${id}`),
  transcript: async (id) => request(`/meetings/${id}/transcript`),
  video: async (id) => request(`/meetings/${id}/video`),
  analyze: async (id) => request(`/meetings/${id}/analyze`, { method: 'POST' }),
  meetingInsight: async (id) => request(`/meetings/${id}/insight`),
  folders: async () => ({ folders: [] }),
  getWeekly: async () => request('/insights/current'),
  generateWeekly: async () => request('/insights/current'),
  listInsights: async () => request('/insights'),
  getInsight: async (id) => request(`/insights/${id}`),
  completeAction: async (id, status = 'completed') =>
    request(`/actions/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
};