import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PublicHeader from '../../components/public/PublicHeader'
import { HERITAGE_COPY, getHeritageChapter } from '../../content/heritageContent'
import { api } from '../../services/api'
import { usePreferredLanguage } from '../../services/language'
import { UI_COPY, type Video } from '../../types'

interface Props {
  slug: string
}

/** Entry page shared by both fixed chapters: hero copy, then one video card that opens the player page. */
export default function ChapterOverviewPage({ slug }: Props) {
  const language = usePreferredLanguage()
  const copy = UI_COPY[language]
  const heritageCopy = HERITAGE_COPY[language]
  const chapter = getHeritageChapter(slug)
  const overview = chapter?.overview
  const [video, setVideo] = useState<Video | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    if (!chapter) return
    setLoading(true)
    setError('')
    api.listPublicVideoSlots(language)
      .then(data => setVideo(data.items.find(slot => slot.slot_key === chapter.slotKey)?.video || null))
      .catch(err => {
        setVideo(null)
        setError(err instanceof Error ? err.message : copy.waking)
      })
      .finally(() => setLoading(false))
  }, [chapter, copy.waking, language])

  useEffect(() => { load() }, [load])

  if (!chapter || !overview) return <main className="heritage-page"><div className="state-card"><p>{copy.empty}</p><Link to="/videos" className="secondary-button">{heritageCopy.home}</Link></div></main>

  return (
    <main className="heritage-page decode-page">
      <PublicHeader language={language} compact />
      <div className="detail-breadcrumb">
        <Link to="/videos" aria-label={heritageCopy.home}><span aria-hidden>⌂</span>{heritageCopy.home}</Link>
        <i aria-hidden>/</i><span>{chapter.menuLabel[language]}</span>
      </div>

      <header className="decode-heading">
        <p className="heritage-eyebrow">{overview.eyebrow[language]}</p>
        <h1>{chapter.menuLabel[language]}</h1>
        <p className="decode-question">{overview.intro[language]}</p>
      </header>

      <section className="decode-results" aria-label={overview.resultLabel[language]}>
        {loading && <div className="state-card" role="status"><span className="spinner" /><p>{copy.loading}</p></div>}
        {!loading && (error || !video) && (
          <div className={`state-card ${error ? 'error-state' : 'warning-state'}`}>
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
