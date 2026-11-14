import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PublicHeader from '../../components/public/PublicHeader'
import { DECODE_COPY, HERITAGE_COPY, getHeritageChapter } from '../../content/heritageContent'
import { api } from '../../services/api'
import { usePreferredLanguage } from '../../services/language'
import { UI_COPY, type Video } from '../../types'

const CHAPTER_SLUG = 'giai-ma-ma-nhai'

export default function DecodeLibraryPage() {
  const language = usePreferredLanguage()
  const copy = UI_COPY[language]
  const heritageCopy = HERITAGE_COPY[language]
  const decodeCopy = DECODE_COPY[language]
  const chapter = getHeritageChapter(CHAPTER_SLUG)!
  const [video, setVideo] = useState<Video | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    api.listPublicVideoSlots(language)
      .then(data => setVideo(data.items.find(slot => slot.slot_key === chapter.slotKey)?.video || null))
      .catch(err => setError(err instanceof Error ? err.message : copy.waking))
      .finally(() => setLoading(false))
  }, [copy.waking, chapter.slotKey, language])

  useEffect(() => { load() }, [load])

  return (
    <main className="heritage-page decode-page">
      <PublicHeader language={language} compact />
      <div className="detail-breadcrumb">
        <Link to="/videos"><span aria-hidden>⌂</span>{heritageCopy.home}</Link>
        <i aria-hidden>/</i><span>{decodeCopy.title}</span>
      </div>

      <header className="decode-heading">
        <p className="heritage-eyebrow">{decodeCopy.eyebrow}</p>
        <h1>{decodeCopy.title}</h1>
        <p className="decode-question">{decodeCopy.question}</p>
      </header>

      <section className="decode-results" aria-label={decodeCopy.result}>
        {loading && <div className="state-card"><span className="spinner" /><p>{copy.loading}</p></div>}
        {!loading && (error || !video) && <div className="state-card error-state"><strong>{copy.videoComingSoon}</strong><p>{error || copy.videoNotBound}</p><button onClick={load} className="secondary-button">{copy.retry}</button></div>}
        {!loading && video && (
          <Link to={`/videos/${chapter.slug}`} className="decode-video-card">
            <div className="decode-video-thumbnail">
              <img src={chapter.thumbnail} alt="" />
            </div>
            <div className="decode-video-copy">
              <h2>{video.title}</h2>
              <p>{video.description}</p>
            </div>
          </Link>
        )}
      </section>
    </main>
  )
}
