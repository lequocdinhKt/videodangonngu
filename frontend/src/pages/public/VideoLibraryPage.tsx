import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatDate, formatDuration } from '../../services/api'
import type { Video } from '../../types'

export default function VideoLibraryPage() {
  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listPublishedVideos()
      .then(data => setVideos(data.items))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-6 text-center text-gray-400">Loading...</div>

  return (
    <div className="min-h-screen p-4 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Videos</h1>
        <Link to="/" className="text-sm text-blue-400">Change Language</Link>
      </div>

      {videos.length === 0 ? (
        <p className="text-gray-400 text-center py-12">No videos available yet.</p>
      ) : (
        <div className="grid gap-4">
          {videos.map(v => (
            <Link
              key={v.id}
              to={`/videos/${v.id}`}
              className="flex gap-4 bg-gray-900 rounded-xl overflow-hidden hover:bg-gray-800 transition"
            >
              {v.thumbnail_url ? (
                <img src={v.thumbnail_url} alt="" className="w-40 h-24 object-cover flex-shrink-0" />
              ) : (
                <div className="w-40 h-24 bg-gray-800 flex-shrink-0" />
              )}
              <div className="p-3 flex flex-col justify-center">
                <h2 className="font-semibold text-lg">{v.title}</h2>
                <p className="text-gray-400 text-sm line-clamp-2">{v.description}</p>
                <div className="flex gap-3 text-xs text-gray-500 mt-1">
                  <span>{formatDuration(v.duration_ms)}</span>
                  <span>{formatDate(v.created_at)}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
