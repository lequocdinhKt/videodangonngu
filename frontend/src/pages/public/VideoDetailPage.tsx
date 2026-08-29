import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import VideoPlayer from '../../components/player/VideoPlayer'
import { api, formatDuration } from '../../services/api'
import type { LanguageCode, Video } from '../../types'

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [video, setVideo] = useState<Video | null>(null)
  const [others, setOthers] = useState<Video[]>([])
  const preferredLang = (localStorage.getItem('preferredLanguage') || 'en-US') as LanguageCode

  useEffect(() => {
    if (!id) return
    api.getVideo(id).then(setVideo).catch(console.error)
    api.listPublishedVideos().then(data => setOthers(data.items.filter(v => v.id !== id))).catch(console.error)
  }, [id])

  if (!video) return <div className="p-6 text-center text-gray-400">Loading...</div>

  return (
    <div className="min-h-screen p-4 max-w-4xl mx-auto space-y-6">
      <VideoPlayer video={video} initialLanguage={preferredLang} />

      <div>
        <h1 className="text-2xl font-bold">{video.title}</h1>
        <p className="text-gray-400 mt-1">{formatDuration(video.duration_ms)}</p>
        <p className="text-gray-300 mt-3">{video.description}</p>
      </div>

      {others.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Other Videos</h2>
          <div className="grid gap-3">
            {others.slice(0, 5).map(v => (
              <Link key={v.id} to={`/videos/${v.id}`} className="flex gap-3 bg-gray-900 rounded-lg p-2 hover:bg-gray-800">
                {v.thumbnail_url && <img src={v.thumbnail_url} alt="" className="w-24 h-14 object-cover rounded" />}
                <div>
                  <p className="font-medium">{v.title}</p>
                  <p className="text-xs text-gray-500">{formatDuration(v.duration_ms)}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <Link to="/videos" className="text-blue-400 text-sm">← Back to library</Link>
    </div>
  )
}
