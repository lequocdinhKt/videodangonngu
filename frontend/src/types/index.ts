export type VideoStatus = 'draft' | 'processing' | 'ready_for_review' | 'published' | 'failed' | 'requires_review'
export type LanguageStatus = 'pending' | 'processing' | 'ready_for_review' | 'completed' | 'failed'
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'
export type LanguageCode = 'vi-VN' | 'en-US' | 'ru-RU' | 'zh-CN'

export interface LanguageDefinition {
  code: LanguageCode
  label: string
  nativeLabel: string
  flag: string
  short: string
}

export const LANGUAGES: LanguageDefinition[] = [
  { code: 'vi-VN', label: 'Tiếng Việt', nativeLabel: 'Tiếng Việt', flag: '🇻🇳', short: 'vi' },
  { code: 'en-US', label: 'English', nativeLabel: 'English', flag: '🇬🇧', short: 'en' },
  { code: 'ru-RU', label: 'Russian', nativeLabel: 'Русский', flag: '🇷🇺', short: 'ru' },
  { code: 'zh-CN', label: 'Chinese', nativeLabel: '中文（简体）', flag: '🇨🇳', short: 'zh' },
]

export const UI_COPY: Record<LanguageCode, Record<string, string>> = {
  'vi-VN': {
    chooseLanguage: 'Chọn ngôn ngữ của bạn',
    chooseLanguageHint: 'Bạn có thể thay đổi lựa chọn bất cứ lúc nào.',
    continue: 'Tiếp tục',
    library: 'Khám phá câu chuyện Việt Nam',
    libraryHint: 'Những thước phim ngắn về văn hóa, di sản và con người.',
    changeLanguage: 'Đổi ngôn ngữ',
    otherVideos: 'Video khác',
    back: 'Quay lại thư viện',
    subtitles: 'Phụ đề',
    subtitlesOff: 'Tắt',
    fullscreen: 'Toàn màn hình',
    loading: 'Đang tải nội dung…',
    waking: 'Máy chủ đang khởi động. Quá trình này có thể mất khoảng một phút.',
    retry: 'Thử lại',
    empty: 'Chưa có video được xuất bản.',
    curated: 'CÂU CHUYỆN CHỌN LỌC',
    explore: 'KHÁM PHÁ TIẾP',
    originalAudio: 'Âm thanh gốc · Phụ đề đa ngôn ngữ',
  },
  'en-US': {
    chooseLanguage: 'Choose your language', chooseLanguageHint: 'You can change it at any time.', continue: 'Continue',
    library: 'Discover stories of Vietnam', libraryHint: 'Short films about culture, heritage and people.', changeLanguage: 'Language',
    otherVideos: 'More videos', back: 'Back to library', subtitles: 'Subtitles', subtitlesOff: 'Off', fullscreen: 'Fullscreen',
    loading: 'Loading content…', waking: 'The server is waking up. This can take about a minute.', retry: 'Try again', empty: 'No published videos yet.',
    curated: 'CURATED VIDEO STORIES', explore: 'CONTINUE EXPLORING', originalAudio: 'Original audio · Multilingual subtitles',
  },
  'ru-RU': {
    chooseLanguage: 'Выберите язык', chooseLanguageHint: 'Язык можно изменить в любое время.', continue: 'Продолжить',
    library: 'Откройте для себя Вьетнам', libraryHint: 'Короткие фильмы о культуре, наследии и людях.', changeLanguage: 'Язык',
    otherVideos: 'Другие видео', back: 'Вернуться', subtitles: 'Субтитры', subtitlesOff: 'Выкл.', fullscreen: 'На весь экран',
    loading: 'Загрузка…', waking: 'Сервер запускается. Это может занять около минуты.', retry: 'Повторить', empty: 'Опубликованных видео пока нет.',
    curated: 'ИЗБРАННЫЕ ВИДЕОИСТОРИИ', explore: 'ПРОДОЛЖИТЬ ЗНАКОМСТВО', originalAudio: 'Оригинальный звук · Многоязычные субтитры',
  },
  'zh-CN': {
    chooseLanguage: '选择语言', chooseLanguageHint: '您可以随时更改语言。', continue: '继续',
    library: '探索越南故事', libraryHint: '关于文化、遗产和人民的短片。', changeLanguage: '语言',
    otherVideos: '更多视频', back: '返回视频列表', subtitles: '字幕', subtitlesOff: '关闭', fullscreen: '全屏',
    loading: '正在加载…', waking: '服务器正在启动，可能需要大约一分钟。', retry: '重试', empty: '暂无已发布的视频。',
    curated: '精选视频故事', explore: '继续探索', originalAudio: '原始音频 · 多语言字幕',
  },
}

export interface VideoTranslation {
  language_code: LanguageCode
  title: string
  description: string
}

export interface VideoLanguage {
  language_code: LanguageCode
  subtitle_url: string | null
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
  translations: VideoTranslation[]
  created_at: string
  updated_at: string
}

export interface ProcessingJob {
  id: string
  pipeline_run_id: string
  stage: string
  language_code: string | null
  status: JobStatus
  progress: number
  error_message: string | null
  retry_count: number
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface PreviewData {
  video_id: string
  status: VideoStatus
  title: string
  description: string
  video_url: string | null
  thumbnail_url: string | null
  languages: VideoLanguage[]
  translations: VideoTranslation[]
  jobs: ProcessingJob[]
}

export interface SubtitleCue {
  id?: string | null
  sequence: number
  start_ms: number
  end_ms: number
  text: string
}

export interface SubtitleTrackEditor {
  language_code: LanguageCode
  status: LanguageStatus
  cues: SubtitleCue[]
}
