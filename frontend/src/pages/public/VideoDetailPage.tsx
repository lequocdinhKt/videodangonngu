import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PublicHeader from '../../components/public/PublicHeader'
import VideoPlayer from '../../components/player/VideoPlayer'
import { HERITAGE_COPY, getHeritageChapter } from '../../content/heritageContent'
import { api } from '../../services/api'
import { usePreferredLanguage } from '../../services/language'
import { UI_COPY, type Video } from '../../types'

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const language = usePreferredLanguage()
  const copy = UI_COPY[language]
  const heritageCopy = HERITAGE_COPY[language]
  const [video, setVideo] = useState<Video | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState('')
  const chapter = getHeritageChapter(id)

  const load = useCallback(() => {
    if (!chapter) return
    setLoaded(false)
    setError('')
    api.listPublicVideoSlots(language)
      .then(data => setVideo(data.items.find(slot => slot.slot_key === chapter.slotKey)?.video || null))
      .catch(err => {
        setVideo(null)
        setError(err instanceof Error ? err.message : copy.waking)
      })
      .finally(() => setLoaded(true))
  }, [chapter, copy.waking, language])

  useEffect(() => { load() }, [load])

  if (!chapter) return <main className="heritage-page"><div className="state-card"><p>{copy.empty}</p><Link to="/videos" className="secondary-button">{heritageCopy.home}</Link></div></main>

  return (
    <main className="heritage-page heritage-detail-page">
      <PublicHeader language={language} compact />
      <div className="detail-breadcrumb">
        <Link to="/videos" aria-label={heritageCopy.home}><span aria-hidden>⌂</span>{heritageCopy.home}</Link>
        <i aria-hidden>/</i><span>{chapter.number} · {chapter.menuLabel[language]}</span>
      </div>

      <header className="detail-title-block">
        <p className="heritage-eyebrow">{heritageCopy.chapter} {chapter.number}</p>
        <h1>{chapter.menuLabel[language]}</h1>
      </header>

      {!loaded && !video && <div className="state-card" role="status"><span className="spinner" /><p>{copy.loading}</p></div>}

      {loaded && !video && (
        <div className="state-card warning-state">
          <div className="state-card-message" role="status">
            <strong>{copy.videoComingSoon}</strong>
            <p>{error || copy.videoNotBound}</p>
          </div>
          <div className="state-card-actions">
            <button type="button" className="secondary-button" onClick={load}>{copy.retry}</button>
            <Link to="/videos" className="secondary-button">{heritageCopy.home}</Link>
          </div>
        </div>
      )}

      {video && (
        <div className="heritage-video-layout">
          <VideoPlayer video={video} initialLanguage={language} />
          <section className="heritage-video-copy" aria-labelledby="video-information-title">
            <h2 id="video-information-title">{video.title}</h2>
            <p>{video.description}</p>
          </section>
        </div>
      )}
    </main>
  )
}
