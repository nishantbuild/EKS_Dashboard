const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  devLogin: (username, password) =>
    request('/auth/dev-login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),
  oidcLoginUrl: () => `${API_BASE}/auth/oidc/login`,

  namespaces: () => request('/api/namespaces'),
  pods: (ns) => request(`/api/${ns}/pods`),
  pod: (ns, name) => request(`/api/${ns}/pods/${name}`),
  podLogs: (ns, name, tailLines = 200) => request(`/api/${ns}/pods/${name}/logs?tail_lines=${tailLines}`),
  deletePod: (ns, name) => request(`/api/${ns}/pods/${name}`, { method: 'DELETE' }),

  deployments: (ns) => request(`/api/${ns}/deployments`),
  deployment: (ns, name) => request(`/api/${ns}/deployments/${name}`),
  scaleDeployment: (ns, name, replicas) =>
    request(`/api/${ns}/deployments/${name}/scale`, { method: 'POST', body: JSON.stringify({ replicas }) }),
  restartDeployment: (ns, name) => request(`/api/${ns}/deployments/${name}/restart`, { method: 'POST' }),

  services: (ns) => request(`/api/${ns}/services`),
  events: (ns) => request(`/api/${ns}/events`),
  podMetrics: (ns) => request(`/api/${ns}/metrics/pods`),

  audit: (limit = 200) => request(`/api/audit?limit=${limit}`),
}

export function wsLogUrl(ns, name) {
  const wsBase = API_BASE.replace(/^http/, 'ws')
  return `${wsBase}/ws/${ns}/pods/${name}/logs`
}

export function wsExecUrl(ns, name, container) {
  const wsBase = API_BASE.replace(/^http/, 'ws')
  const q = container ? `?container=${encodeURIComponent(container)}` : ''
  return `${wsBase}/ws/${ns}/pods/${name}/exec${q}`
}
