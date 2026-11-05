import type {
  LanguageCode,
  PreviewData,
  SubtitleTrackEditor,
  Video,
  VideoTranslation,
} from '../types'
import { LANGUAGES } from '../types'

const API_ORIGIN = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const API = `${API_ORIGIN}/api`
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

interface DemoManifestItem {
  slug: string
  video: string
  preview_video?: string
  thumbnail: string
  subtitles: Record<LanguageCode, string>
  translations: VideoTranslation[]
}

let demoManifestPromise: Promise<DemoManifestItem[]> | null = null

async function loadDemoVideos(language: LanguageCode): Promise<Video[]> {
  demoManifestPromise ||= fetch('/demo/manifest.json').then(response => {
    if (!response.ok) throw new Error('Chưa tạo dữ liệu demo. Chạy python demo/generate_demo_assets.py.')
    return response.json()
  })
  const manifest = await demoManifestPromise
  const now = new Date().toISOString()
  return manifest.map(item => {
    const localized = item.translations.find(translation => translation.language_code === language)
      || item.translations.find(translation => translation.language_code === 'vi-VN')!
    return {
      id: item.slug,
      title: localized.title,
      description: localized.description,
      status: 'published',
      duration_ms: 10_000,
      thumbnail_url: `/demo/${item.thumbnail}`,
      video_url: `/demo/${item.preview_video || item.video}`,
      languages: LANGUAGES.map(definition => ({
        language_code: definition.code,
        subtitle_url: `/demo/${item.subtitles[definition.code]}`,
        status: 'completed',
      })),
      translations: item.translations,
      created_at: now,
      updated_at: now,
    }
  })
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function absoluteMediaUrl(url: string | null): string | null {
  if (!url || /^(https?:|data:|blob:)/.test(url)) return url
  return `${API_ORIGIN}${url}`
}

function normalizeVideo(video: Video): Video {
  return {
    ...video,
    video_url: absoluteMediaUrl(video.video_url),
    thumbnail_url: absoluteMediaUrl(video.thumbnail_url),
    languages: video.languages.map(item => ({ ...item, subtitle_url: absoluteMediaUrl(item.subtitle_url) })),
  }
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 75_000)
  try {
    const res = await fetch(url, {
      ...options,
      headers: { ...authHeaders(), ...options.headers },
      signal: options.signal || controller.signal,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      const detail = err.detail
      const message = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join('; ')
          : 'Request failed'
      throw new Error(message || `HTTP ${res.status}`)
    }
    return res.json()
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Máy chủ đang khởi động hoặc phản hồi quá chậm. Vui lòng thử lại.')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

async function uploadAsset(videoId: string, kind: 'video' | 'thumbnail' | 'subtitle', file: File, languageCode?: LanguageCode, onProgress?: (value: number) => void) {
  const signed = await request<{
    key: string
    upload_url: string | null
    fallback_url: string | null
    method: 'PUT' | 'POST'
    headers: Record<string, string>
  }>(`${API}/admin/videos/${videoId}/upload-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      kind,
      filename: file.name,
      content_type: file.type || 'application/octet-stream',
      size_bytes: file.size,
      language_code: languageCode,
    }),
  })

  if (signed.upload_url) {
    const response = await fetch(signed.upload_url, { method: 'PUT', headers: signed.headers, body: file })
    if (!response.ok) throw new Error(`Upload ${kind} thất bại (HTTP ${response.status})`)
    onProgress?.(100)
  } else if (signed.fallback_url) {
    await new Promise<void>((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', absoluteMediaUrl(signed.fallback_url) || signed.fallback_url)
      const token = localStorage.getItem('token')
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      xhr.upload.onprogress = event => {
        if (event.lengthComputable) onProgress?.(Math.round(event.loaded / event.total * 100))
      }
      xhr.onload = () => xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload ${kind} thất bại`))
      xhr.onerror = () => reject(new Error('Lỗi mạng khi upload'))
      const form = new FormData()
      form.append('file', file)
      xhr.send(form)
    })
  } else {
    throw new Error('Không nhận được địa chỉ upload')
  }

  await request(`${API}/admin/videos/${videoId}/assets/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, key: signed.key, language_code: languageCode }),
  })
}

export function adminMediaUrl(path: string): string {
  const url = absoluteMediaUrl(path) || path
  const token = localStorage.getItem('token')
  return token ? `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}` : url
}

export const api = {
  login: (email: string, password: string) => request<{ access_token: string }>(`${API}/admin/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
  }),
  listVideos: () => request<{ items: Video[]; total: number }>(`${API}/admin/videos`).then(data => ({ ...data, items: data.items.map(normalizeVideo) })),
  listPublishedVideos: (lang: LanguageCode) => DEMO_MODE
    ? loadDemoVideos(lang).then(items => ({ items, total: items.length }))
    : request<{ items: Video[]; total: number }>(`${API}/videos?lang=${encodeURIComponent(lang)}`).then(data => ({ ...data, items: data.items.map(normalizeVideo) })),
  getVideo: (id: string, lang: LanguageCode) => DEMO_MODE
    ? loadDemoVideos(lang).then(items => {
        const video = items.find(item => item.id === id)
        if (!video) throw new Error('Video không tồn tại')
        return video
      })
    : request<Video>(`${API}/videos/${id}?lang=${encodeURIComponent(lang)}`).then(normalizeVideo),
  createDraft: (translations: VideoTranslation[]) => request<{ id: string }>(`${API}/admin/videos/draft`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ translations }),
  }),
  updateTranslations: (id: string, translations: VideoTranslation[]) => request(`${API}/admin/videos/${id}/translations`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ translations }),
  }),
  uploadAsset,
  generate: (id: string) => request(`${API}/admin/videos/${id}/generate`, { method: 'POST' }),
  regenerate: (id: string, lang: string) => request(`${API}/admin/videos/${id}/regenerate/${lang}`, { method: 'POST' }),
  preview: (id: string) => request<PreviewData>(`${API}/admin/videos/${id}/preview`).then(data => ({
    ...data,
    video_url: absoluteMediaUrl(data.video_url),
    thumbnail_url: absoluteMediaUrl(data.thumbnail_url),
    languages: data.languages.map(item => ({ ...item, subtitle_url: absoluteMediaUrl(item.subtitle_url) })),
  })),
  getSubtitleCues: (id: string, lang: LanguageCode) => request<SubtitleTrackEditor>(`${API}/admin/videos/${id}/subtitles/${lang}`),
  saveSubtitleCues: (id: string, lang: LanguageCode, cues: SubtitleTrackEditor['cues'], approved: boolean) => request<SubtitleTrackEditor>(`${API}/admin/videos/${id}/subtitles/${lang}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cues, approved }),
  }),
  publish: (id: string) => request(`${API}/admin/videos/${id}/publish`, { method: 'POST' }),
  unpublish: (id: string) => request(`${API}/admin/videos/${id}/unpublish`, { method: 'POST' }),
  deleteVideo: (id: string) => request(`${API}/admin/videos/${id}`, { method: 'DELETE' }),
  getQR: () => request<{ url: string; qr_image_base64: string; qr_svg_base64: string }>(`${API}/admin/qr`),
}

export function formatDuration(ms: number | null): string {
  if (!ms) return '--:--'
  const totalSec = Math.floor(ms / 1000)
  return `${Math.floor(totalSec / 60)}:${(totalSec % 60).toString().padStart(2, '0')}`
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
