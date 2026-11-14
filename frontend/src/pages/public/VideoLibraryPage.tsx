import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import PublicHeader from '../../components/public/PublicHeader'
import projectPoster from '../../assets/ma-nhai-project-poster.jpg'
import { HERITAGE_CHAPTERS, HERITAGE_COPY, PROJECT_INTRO } from '../../content/heritageContent'
import { api } from '../../services/api'
import { usePreferredLanguage } from '../../services/language'
import { UI_COPY, type VideoSlot } from '../../types'

export default function VideoLibraryPage() {
  const language = usePreferredLanguage()
  const copy = UI_COPY[language]
  const heritageCopy = HERITAGE_COPY[language]
  const [slots, setSlots] = useState<VideoSlot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    api.listPublicVideoSlots(language)
      .then(data => setSlots(data.items))
      .catch(err => setError(err instanceof Error ? err.message : copy.waking))
      .finally(() => setLoading(false))
  }, [copy.waking, language])

  useEffect(() => { load() }, [load])

  const chapters = useMemo(() => HERITAGE_CHAPTERS.map(chapter => ({
    chapter,
    video: slots.find(slot => slot.slot_key === chapter.slotKey)?.video || null,
  })), [slots])

  return (
    <main className="heritage-page heritage-library-page" lang={language}>
      <div className="library-intro-panel">
        <PublicHeader language={language} />

        <section className="heritage-hero project-intro-hero">
          <figure className="project-poster">
            <img src={projectPoster} alt="Poster giới thiệu dự án Ma nhai Ngũ Hành Sơn" />
          </figure>
          <div className="heritage-hero-copy project-intro-copy">
            <p className="heritage-eyebrow">{heritageCopy.eyebrow}</p>
            <h1>{heritageCopy.welcome}</h1>
            <div className="project-intro-text">
              {PROJECT_INTRO[language].map(paragraph => <p key={paragraph}>{paragraph}</p>)}
            </div>
          </div>
        </section>

        <a href="#chapters" className="heritage-scroll-link library-scroll-link">
          <span aria-hidden>
            <svg viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" /></svg>
          </span>{heritageCopy.explore}
        </a>
      </div>

      <section id="chapters" className="heritage-chapters">
        <div className="heritage-section-heading">
          <h2>{heritageCopy.explore}</h2>
        </div>

        {loading && <div className="state-card"><span className="spinner" /><p>{copy.loading}</p></div>}
        {!loading && error && <div className="state-card error-state"><strong>{copy.waking}</strong><p>{error}</p><button onClick={load} className="secondary-button">{copy.retry}</button></div>}

        {!loading && !error && (
          <div className="heritage-story-list">
            {chapters.map(({ chapter, video }) => (
              <Link key={chapter.slug} to={chapter.route} className="heritage-story-card">
                <div className="heritage-story-image">
                  <img src={chapter.thumbnail} alt="" />
                </div>
                <div className="heritage-story-copy">
                  <h3>{video?.title || chapter.title[language]}</h3>
                  <p>{video?.description || chapter.description[language]}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

    </main>
  )
}
