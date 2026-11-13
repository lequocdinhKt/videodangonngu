import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import PublicHeader from '../../components/public/PublicHeader'
import { HERITAGE_CHAPTERS, HERITAGE_COPY, PROJECT_INTRO, localizeHeritageVideo } from '../../content/heritageContent'
import { api, formatDuration } from '../../services/api'
import { UI_COPY, type LanguageCode, type Video } from '../../types'

export default function VideoLibraryPage() {
  const language = (localStorage.getItem('preferredLanguage') || 'vi-VN') as LanguageCode
  const copy = UI_COPY[language]
  const heritageCopy = HERITAGE_COPY[language]
  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    api.listPublishedVideos(language)
      .then(data => setVideos(data.items.map(video => localizeHeritageVideo(video, language))))
      .catch(err => setError(err instanceof Error ? err.message : copy.waking))
      .finally(() => setLoading(false))
  }, [copy.waking, language])

  useEffect(() => { load() }, [load])

  const chapters = useMemo(() => HERITAGE_CHAPTERS.map(chapter => ({
    chapter,
    video: videos.find(video => video.id === chapter.videoId),
  })), [videos])

  return (
    <main className="heritage-page heritage-library-page">
      <div className="library-intro-panel">
        <PublicHeader language={language} />

        <section className="heritage-hero project-intro-hero">
          <figure className="project-poster project-poster-placeholder">
            <div className="project-poster-empty" role="img" aria-label="Chưa có ảnh poster">
              <svg viewBox="0 0 48 48" aria-hidden="true">
                <path d="M8 7h32a4 4 0 0 1 4 4v26a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V11a4 4 0 0 1 4-4Z" />
                <circle cx="34" cy="17" r="4" />
                <path d="m5 34 11-11a3 3 0 0 1 4 0l8 8 4-4a3 3 0 0 1 4 0l8 8" />
              </svg>
            </div>
          </figure>
          <div className="heritage-hero-copy project-intro-copy">
            <p className="heritage-eyebrow">{heritageCopy.eyebrow}</p>
            <h1>{heritageCopy.welcome}</h1>
            <div className="project-intro-text">
              {PROJECT_INTRO[language].map(paragraph => <p key={paragraph}>{paragraph}</p>)}
            </div>
            <a href="#chapters" className="heritage-scroll-link">
              <span aria-hidden>
                <svg viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" /></svg>
              </span>{heritageCopy.explore}
            </a>
          </div>
        </section>
      </div>

      <section id="chapters" className="heritage-chapters">
        <div className="heritage-section-heading">
          <div><p className="heritage-eyebrow">02 {heritageCopy.chapter.toUpperCase()}</p><h2>{heritageCopy.explore}</h2></div>
          <p>{heritageCopy.exploreHint}</p>
        </div>

        {loading && <div className="state-card"><span className="spinner" /><p>{copy.loading}</p></div>}
        {!loading && error && <div className="state-card error-state"><strong>{copy.waking}</strong><p>{error}</p><button onClick={load} className="secondary-button">{copy.retry}</button></div>}

        {!loading && !error && (
          <div className="heritage-story-list">
            {chapters.map(({ chapter, video }) => (
              <Link key={chapter.videoId} to={chapter.route} className="heritage-story-card">
                <div className="heritage-story-image">
                  <img src={chapter.thumbnail} alt="" />
                  <span className="heritage-play" aria-hidden>▶</span>
                </div>
                <div className="heritage-story-copy">
                  <p><span>{chapter.number}</span>{heritageCopy.chapter}</p>
                  <h3>{chapter.title[language]}</h3>
                  <div className="story-meta">
                    <span>{formatDuration(video?.duration_ms || 0)}</span>
                    <strong>{heritageCopy.watch}<i aria-hidden>→</i></strong>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

    </main>
  )
}
