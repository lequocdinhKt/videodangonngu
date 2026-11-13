import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PublicHeader from '../../components/public/PublicHeader'
import VideoPlayer from '../../components/player/VideoPlayer'
import { HERITAGE_COPY, getHeritageChapter, getHeritageChapterForProductionVideo, localizeHeritageVideo } from '../../content/heritageContent'
import { api } from '../../services/api'
import { LANGUAGES, UI_COPY, type LanguageCode, type Video } from '../../types'

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const language = (localStorage.getItem('preferredLanguage') || 'vi-VN') as LanguageCode
  const copy = UI_COPY[language]
  const heritageCopy = HERITAGE_COPY[language]
  const [video, setVideo] = useState<Video | null>(null)
  const chapter = getHeritageChapter(id) || (id ? getHeritageChapterForProductionVideo(id) : undefined)
  const previewVideo: Video | null = chapter ? {
    id: chapter.productionVideoId || chapter.slug,
    title: chapter.title[language],
    description: chapter.description[language],
    status: 'published',
    duration_ms: null,
    thumbnail_url: chapter.thumbnail,
    video_url: null,
    languages: LANGUAGES.map(item => ({ language_code: item.code, subtitle_url: null, status: 'pending' })),
    translations: [],
    created_at: '',
    updated_at: '',
  } : null
  const shownVideo = video || previewVideo

  const load = useCallback(() => {
    if (!chapter?.productionVideoId) return
    api.getVideo(chapter.productionVideoId, language)
      .then(current => setVideo(localizeHeritageVideo(current, language)))
      .catch(() => setVideo(null))
  }, [chapter?.productionVideoId, language])

  useEffect(() => { load() }, [load])

  if (!chapter) return <main className="heritage-page"><div className="state-card"><p>{copy.empty}</p><Link to="/videos" className="secondary-button">{heritageCopy.home}</Link></div></main>
  if (!chapter.productionVideoId) return <main className="heritage-page"><div className="state-card error-state" role="status"><strong>{copy.videoComingSoon}</strong><p>{copy.videoNotBound}</p><Link to="/videos" className="secondary-button">{heritageCopy.home}</Link></div></main>

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

      {shownVideo && <>
        <VideoPlayer video={shownVideo} initialLanguage={language} />
      </>}
    </main>
  )
}
