import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PublicHeader from '../../components/public/PublicHeader'
import VideoPlayer from '../../components/player/VideoPlayer'
import { HERITAGE_CHAPTERS, HERITAGE_COPY, localizeHeritageVideo } from '../../content/heritageContent'
import { api } from '../../services/api'
import { UI_COPY, type LanguageCode, type Video } from '../../types'

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const language = (localStorage.getItem('preferredLanguage') || 'vi-VN') as LanguageCode
  const copy = UI_COPY[language]
  const heritageCopy = HERITAGE_COPY[language]
  const [video, setVideo] = useState<Video | null>(null)
  const [error, setError] = useState('')
  const chapterIndex = HERITAGE_CHAPTERS.findIndex(item => item.videoId === id)
  const chapter = HERITAGE_CHAPTERS[chapterIndex]
  const nextChapter = HERITAGE_CHAPTERS[(chapterIndex + 1) % HERITAGE_CHAPTERS.length]

  const load = useCallback(() => {
    if (!id) return
    setError('')
    api.getVideo(id, language)
      .then(current => setVideo(localizeHeritageVideo(current, language)))
      .catch(err => setError(err instanceof Error ? err.message : copy.waking))
  }, [copy.waking, id, language])

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

      {!video && <div className={`state-card ${error ? 'error-state' : ''}`}>
        {error ? <><strong>{copy.waking}</strong><p>{error}</p><button onClick={load} className="secondary-button">{copy.retry}</button></> : <><span className="spinner" /><p>{copy.loading}</p></>}
      </div>}

      {video && <>
        <VideoPlayer video={video} initialLanguage={language} />
        <article className="heritage-video-copy">
          <div className="heritage-ornament" aria-hidden><span>◆</span><i /><span>◆</span></div>
          <h2>{video.title}</h2>
          <p>{video.description}</p>
          <div className="heritage-note"><span>CC</span><p>{copy.originalAudio}<small>{copy.subtitles}: VI · EN · RU · ZH</small></p></div>
        </article>

        {nextChapter && nextChapter.videoId !== chapter.videoId && (
          <Link to={`/videos/${nextChapter.videoId}`} className="next-chapter-card">
            <img src={nextChapter.thumbnail} alt="" />
            <div><p>{heritageCopy.next}</p><strong>{nextChapter.menuLabel[language]}</strong><span>{heritageCopy.watch} →</span></div>
          </Link>
        )}
      </>}
    </main>
  )
}
