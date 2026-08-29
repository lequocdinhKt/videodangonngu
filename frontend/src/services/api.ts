import type { PreviewData, Video } from '../types'

const API = '/api'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...options.headers },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>(`${API}/admin/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),

  listVideos: () => request<{ items: Video[]; total: number }>(`${API}/admin/videos`),

  listPublishedVideos: () => request<{ items: Video[]; total: number }>(`${API}/videos`),

  getVideo: (id: string) => request<Video>(`${API}/videos/${id}`),

  createVideo: (formData: FormData) =>
    request<{ id: string }>(`${API}/admin/videos`, { method: 'POST', body: formData }),

  generate: (id: string) =>
    request(`${API}/admin/videos/${id}/generate`, { method: 'POST' }),

  regenerate: (id: string, lang: string) =>
    request(`${API}/admin/videos/${id}/regenerate/${lang}`, { method: 'POST' }),

  getJobs: (id: string) => request(`${API}/admin/videos/${id}/jobs`),

  preview: (id: string) => request<PreviewData>(`${API}/admin/videos/${id}/preview`),

  publish: (id: string) => request(`${API}/admin/videos/${id}/publish`, { method: 'POST' }),

  unpublish: (id: string) => request(`${API}/admin/videos/${id}/unpublish`, { method: 'POST' }),

  deleteVideo: (id: string) => request(`${API}/admin/videos/${id}`, { method: 'DELETE' }),

  getQR: () => request<{ url: string; qr_image_base64: string }>(`${API}/admin/qr`),
}

export function formatDuration(ms: number | null): string {
  if (!ms) return '--:--'
  const totalSec = Math.floor(ms / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return `${min}:${sec.toString().padStart(2, '0')}`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
