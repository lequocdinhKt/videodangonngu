export type CaptionPosition = 'top' | 'center' | 'bottom'
export type CaptionFontSize = 'small' | 'medium' | 'large'

export interface CaptionPreferences {
  position: CaptionPosition
  fontSize: CaptionFontSize
  backgroundOpacity: number
}

export const DEFAULT_CAPTION_PREFERENCES: CaptionPreferences = {
  position: 'bottom',
  fontSize: 'medium',
  backgroundOpacity: 75,
}

const STORAGE_KEY = 'video-guide:caption-preferences:v1'

function isCaptionPosition(value: unknown): value is CaptionPosition {
  return value === 'top' || value === 'center' || value === 'bottom'
}

function isCaptionFontSize(value: unknown): value is CaptionFontSize {
  return value === 'small' || value === 'medium' || value === 'large'
}

function isPreferences(value: unknown): value is CaptionPreferences {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<CaptionPreferences>
  return isCaptionPosition(candidate.position)
    && isCaptionFontSize(candidate.fontSize)
    && typeof candidate.backgroundOpacity === 'number'
    && Number.isFinite(candidate.backgroundOpacity)
    && candidate.backgroundOpacity >= 0
    && candidate.backgroundOpacity <= 100
}

export function readCaptionPreferences(): CaptionPreferences {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    return isPreferences(saved) ? saved : DEFAULT_CAPTION_PREFERENCES
  } catch {
    return DEFAULT_CAPTION_PREFERENCES
  }
}

export function saveCaptionPreferences(preferences: CaptionPreferences) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
  } catch {
    // Captions remain usable when storage is unavailable (private/embed modes).
  }
}
