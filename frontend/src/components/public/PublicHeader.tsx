import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { HERITAGE_CHAPTERS, HERITAGE_COPY } from '../../content/heritageContent'
import { LANGUAGES, type LanguageCode } from '../../types'

interface Props {
  language: LanguageCode
  compact?: boolean
}

export default function PublicHeader({ language, compact = false }: Props) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const copy = HERITAGE_COPY[language]
  const currentLanguage = LANGUAGES.find(item => item.code === language) || LANGUAGES[0]

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  return (
    <header className={`heritage-header ${compact ? 'is-compact' : ''}`}>
      <Link to="/videos" className="heritage-brand" aria-label={copy.home}>
        <span className="heritage-seal" aria-hidden>五</span>
        <span><small>DI SẢN ĐÀ NẴNG</small><strong>{copy.siteName}</strong></span>
      </Link>
      <div className="heritage-header-actions">
        <Link to="/?change=1" className="heritage-language" aria-label={copy.home}>
          <span aria-hidden>{currentLanguage.flag}</span><span className="language-name">{currentLanguage.nativeLabel}</span>
        </Link>
        <div className="heritage-menu-wrap" ref={menuRef}>
          <button type="button" className={`menu-trigger ${open ? 'is-open' : ''}`} onClick={() => setOpen(value => !value)} aria-expanded={open} aria-label={copy.menu}>
            <span /><span /><span />
          </button>
          {open && (
            <nav className="chapter-menu" aria-label={copy.menu}>
              <div className="chapter-menu-title"><span>{copy.menu}</span><small>02</small></div>
              {HERITAGE_CHAPTERS.map(chapter => (
                <Link key={chapter.videoId} to={`/videos/${chapter.videoId}`} onClick={() => setOpen(false)}>
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
