import { useEffect, useState } from 'react'
import type { LanguageCode } from '../types'

const LANGUAGE_CHANGED_EVENT = 'preferred-language-changed'
const FALLBACK_LANGUAGE: LanguageCode = 'vi-VN'
const LANGUAGE_CODES: LanguageCode[] = ['vi-VN', 'en-US', 'ru-RU', 'zh-CN']

export function getPreferredLanguage(): LanguageCode {
  const saved = localStorage.getItem('preferredLanguage')
  return LANGUAGE_CODES.includes(saved as LanguageCode) ? saved as LanguageCode : FALLBACK_LANGUAGE
}

export function setPreferredLanguage(language: LanguageCode) {
  localStorage.setItem('preferredLanguage', language)
  window.dispatchEvent(new Event(LANGUAGE_CHANGED_EVENT))
}

export function usePreferredLanguage() {
  const [language, setLanguage] = useState<LanguageCode>(getPreferredLanguage)

  useEffect(() => {
    const syncLanguage = () => setLanguage(getPreferredLanguage())
    window.addEventListener(LANGUAGE_CHANGED_EVENT, syncLanguage)
    window.addEventListener('storage', syncLanguage)
    return () => {
      window.removeEventListener(LANGUAGE_CHANGED_EVENT, syncLanguage)
      window.removeEventListener('storage', syncLanguage)
    }
  }, [])

  return language
}
