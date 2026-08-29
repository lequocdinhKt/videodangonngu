export type VideoStatus = 'draft' | 'processing' | 'ready_for_review' | 'published' | 'failed' | 'requires_review'
export type LanguageStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface VideoLanguage {
  language_code: string
  subtitle_url: string | null
  audio_url: string | null
  status: LanguageStatus
}

export interface Video {
  id: string
  title: string
  description: string
  status: VideoStatus
  duration_ms: number | null
  thumbnail_url: string | null
  video_url: string | null
  languages: VideoLanguage[]
  created_at: string
  updated_at: string
}

export interface ProcessingJob {
  id: string
  stage: string
  language_code: string | null
  status: JobStatus
  progress: number
  error_message: string | null
  retry_count: number
  created_at: string
}

export interface PreviewData {
  video_id: string
  status: VideoStatus
  video_url: string | null
  thumbnail_url: string | null
  languages: VideoLanguage[]
  jobs: ProcessingJob[]
}

export type LanguageCode = 'vi-VN' | 'en-US' | 'ru-RU' | 'zh-CN'

export const LANGUAGES: { code: LanguageCode; label: string; flag: string; short: string }[] = [
  { code: 'vi-VN', label: 'Vietnamese', flag: '🇻🇳', short: 'vi' },
  { code: 'en-US', label: 'English', flag: '🇬🇧', short: 'en' },
  { code: 'ru-RU', label: 'Russian', flag: '🇷🇺', short: 'ru' },
  { code: 'zh-CN', label: 'Chinese', flag: '🇨🇳', short: 'zh' },
]

export interface SubtitleSettings {
  enabled: boolean
  fontSize: number
  textColor: string
  textOpacity: number
  bgColor: string
  bgOpacity: number
  position: 'top' | 'center' | 'bottom'
}

export const DEFAULT_SUBTITLE_SETTINGS: SubtitleSettings = {
  enabled: true,
  fontSize: 18,
  textColor: '#ffffff',
  textOpacity: 1,
  bgColor: '#000000',
  bgOpacity: 0.6,
  position: 'bottom',
}
