import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import PublicHeader from '../../components/public/PublicHeader'
import { HERITAGE_CHAPTERS, HERITAGE_COPY, localizeHeritageVideo } from '../../content/heritageContent'
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
    <main className="heritage-page">
      <PublicHeader language={language} />

      <section className="heritage-hero">
        <div className="heritage-hero-copy">
          <p className="heritage-eyebrow">{heritageCopy.eyebrow}</p>
          <h1>{heritageCopy.welcome}</h1>
          <p>{heritageCopy.introduction}</p>
          <a href="#chapters" className="heritage-scroll-link">
            <span aria-hidden>↓</span>{heritageCopy.explore}
          </a>
        </div>
        <div className="heritage-hero-art" aria-label={HERITAGE_CHAPTERS[0].menuLabel[language]}>
          <img src={HERITAGE_CHAPTERS[0].thumbnail} alt="" />
          <div className="hero-art-caption"><span>16°00′N</span><strong>NGŨ HÀNH SƠN</strong><span>108°15′E</span></div>
        </div>
      </section>

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
              <Link key={chapter.videoId} to={`/videos/${chapter.videoId}`} className="heritage-story-card">
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

      <footer className="heritage-footer">
        <span className="heritage-seal mini" aria-hidden>五</span>
        <p>{heritageCopy.siteName}<small>{copy.originalAudio}</small></p>
        <span>ĐÀ NẴNG · VIỆT NAM</span>
      </footer>
    </main>
  )
}
