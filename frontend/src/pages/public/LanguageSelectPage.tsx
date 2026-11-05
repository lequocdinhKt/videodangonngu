import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LANGUAGES, UI_COPY, type LanguageCode } from '../../types'

export default function LanguageSelectPage() {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<LanguageCode>('vi-VN')

  useEffect(() => {
    const saved = localStorage.getItem('preferredLanguage') as LanguageCode | null
    const change = new URLSearchParams(window.location.search).has('change')
    if (saved && !change) navigate('/videos', { replace: true })
    else if (saved) setSelected(saved)
  }, [navigate])

  const copy = UI_COPY[selected]
  const handleContinue = () => {
    localStorage.setItem('preferredLanguage', selected)
    navigate('/videos')
  }

  return (
    <main className="language-page">
      <section className="language-panel" aria-labelledby="language-title">
        <div className="heritage-seal language-seal" aria-hidden>五</div>
        <p className="eyebrow">DI SẢN · NGŨ HÀNH SƠN</p>
        <h1 id="language-title">{copy.chooseLanguage}</h1>
        <p className="lead">{copy.chooseLanguageHint}</p>
        <div className="language-grid" role="radiogroup" aria-label={copy.chooseLanguage}>
          {LANGUAGES.map(language => (
            <button key={language.code} type="button" role="radio" aria-checked={selected === language.code}
              onClick={() => setSelected(language.code)} className={`language-card ${selected === language.code ? 'is-selected' : ''}`}>
              <span className="flag" aria-hidden>{language.flag}</span>
              <span><strong>{language.nativeLabel}</strong><small>{language.code}</small></span>
              <span className="selection-dot" aria-hidden />
            </button>
          ))}
        </div>
        <button type="button" className="primary-button wide" onClick={handleContinue}>{copy.continue} <span aria-hidden>→</span></button>
      </section>
      <aside className="language-visual" aria-hidden>
        <div className="visual-orb visual-orb-one" /><div className="visual-orb visual-orb-two" />
        <div className="visual-card"><span>04</span><strong>languages</strong><div className="visual-line" /><small>Ma nhai · Ngũ Hành Sơn</small></div>
      </aside>
    </main>
  )
}
