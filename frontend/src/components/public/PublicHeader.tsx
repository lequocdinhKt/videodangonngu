import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { HERITAGE_CHAPTERS, HERITAGE_COPY } from '../../content/heritageContent'
import { setPreferredLanguage } from '../../services/language'
import { LANGUAGES, UI_COPY, type LanguageCode } from '../../types'

interface Props {
  language: LanguageCode
  compact?: boolean
}

export default function PublicHeader({ language, compact = false }: Props) {
  const [open, setOpen] = useState(false)
  const [languageOpen, setLanguageOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  const languagePickerRef = useRef<HTMLDivElement>(null)
  const languageButtonRef = useRef<HTMLButtonElement>(null)
  const copy = HERITAGE_COPY[language]
  const uiCopy = UI_COPY[language]
  const currentLanguage = LANGUAGES.find(item => item.code === language) || LANGUAGES[0]

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setOpen(false)
      if (languagePickerRef.current && !languagePickerRef.current.contains(event.target as Node)) setLanguageOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  useEffect(() => {
    if (!open && !languageOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setOpen(false)
      setLanguageOpen(false)
      if (open) menuButtonRef.current?.focus()
      else languageButtonRef.current?.focus()
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [languageOpen, open])

  const selectLanguage = (nextLanguage: LanguageCode) => {
    setPreferredLanguage(nextLanguage)
    setLanguageOpen(false)
    languageButtonRef.current?.focus()
  }

  return (
    <header className={`heritage-header ${compact ? 'is-compact' : ''}`}>
      <Link to="/videos" className="heritage-brand" aria-label={copy.home}>
        <span><small>DI SẢN ĐÀ NẴNG</small><strong>{copy.siteName}</strong></span>
      </Link>
      <div className="heritage-header-actions">
        <div className="heritage-language-picker" ref={languagePickerRef}>
          <button ref={languageButtonRef} type="button" className="heritage-language" onClick={() => { setLanguageOpen(value => !value); setOpen(false) }} aria-expanded={languageOpen} aria-controls="heritage-language-menu" aria-label={uiCopy.changeLanguage}>
          <span aria-hidden>{currentLanguage.flag}</span><span className="language-name">{currentLanguage.nativeLabel}</span>
          </button>
          {languageOpen && (
            <div id="heritage-language-menu" className="language-popover" role="group" aria-label={uiCopy.changeLanguage}>
              {LANGUAGES.map(item => (
                <button key={item.code} type="button" aria-pressed={item.code === language} className={item.code === language ? 'is-selected' : ''} onClick={() => selectLanguage(item.code)}>
                  <span aria-hidden>{item.flag}</span><span>{item.nativeLabel}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="heritage-menu-wrap" ref={menuRef}>
          <button ref={menuButtonRef} type="button" className={`menu-trigger ${open ? 'is-open' : ''}`} onClick={() => { setOpen(value => !value); setLanguageOpen(false) }} aria-expanded={open} aria-controls="heritage-chapter-menu" aria-label={copy.menu}>
            <span /><span /><span />
          </button>
          {open && (
            <nav id="heritage-chapter-menu" className="chapter-menu" aria-label={copy.menu}>
              <div className="chapter-menu-title"><span>{copy.menu}</span><small>02</small></div>
              {HERITAGE_CHAPTERS.map(chapter => (
                <Link key={chapter.slug} to={chapter.route} onClick={() => setOpen(false)}>
                  <span>{chapter.number}</span><strong>{chapter.menuLabel[language]}</strong><i aria-hidden>↗</i>
                </Link>
              ))}
            </nav>
          )}
        </div>
      </div>
    </header>
  )
}
