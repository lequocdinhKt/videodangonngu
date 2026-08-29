import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, formatDate, formatDuration } from '../../services/api'
import type { Video } from '../../types'

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-600',
  processing: 'bg-yellow-600',
  ready_for_review: 'bg-blue-600',
  published: 'bg-green-600',
  failed: 'bg-red-600',
  requires_review: 'bg-orange-600',
}

export default function AdminDashboardPage() {
  const navigate = useNavigate()
  const [videos, setVideos] = useState<Video[]>([])
  const [qr, setQr] = useState<string | null>(null)

  useEffect(() => {
    if (!localStorage.getItem('token')) { navigate('/admin/login'); return }
    api.listVideos().then(d => setVideos(d.items)).catch(() => navigate('/admin/login'))
    api.getQR().then(d => setQr(d.qr_image_base64)).catch(() => {})
  }, [navigate])

  const handlePublish = async (id: string) => {
    await api.publish(id)
    setVideos(v => v.map(x => x.id === id ? { ...x, status: 'published' } : x))
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this video?')) return
    await api.deleteVideo(id)
    setVideos(v => v.filter(x => x.id !== id))
  }

  return (
    <div className="min-h-screen p-4 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex gap-3">
          <Link to="/admin/videos/new" className="px-4 py-2 bg-blue-600 rounded-lg text-sm font-semibold">+ New Video</Link>
          <button onClick={() => { localStorage.removeItem('token'); navigate('/admin/login') }} className="px-4 py-2 bg-gray-700 rounded-lg text-sm">Logout</button>
        </div>
      </div>

      {qr && (
        <div className="mb-6 bg-gray-900 p-4 rounded-xl inline-block">
          <p className="text-sm text-gray-400 mb-2">QR Code for public access</p>
          <img src={qr} alt="QR Code" className="w-32 h-32" />
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-gray-800">
              <th className="p-3">Title</th>
              <th className="p-3">Status</th>
              <th className="p-3">Languages</th>
              <th className="p-3">Duration</th>
              <th className="p-3">Created</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {videos.map(v => (
              <tr key={v.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                <td className="p-3 font-medium">{v.title}</td>
                <td className="p-3"><span className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[v.status]}`}>{v.status}</span></td>
                <td className="p-3">
                  <div className="flex gap-1 flex-wrap">
                    {v.languages.map(l => (
                      <span key={l.language_code} className={`text-xs px-1.5 py-0.5 rounded ${l.status === 'completed' ? 'bg-green-800' : 'bg-gray-700'}`}>
                        {l.language_code.split('-')[0]}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="p-3">{formatDuration(v.duration_ms)}</td>
                <td className="p-3">{formatDate(v.created_at)}</td>
                <td className="p-3">
                  <div className="flex gap-2 flex-wrap">
                    <Link to={`/admin/videos/${v.id}`} className="text-blue-400 hover:underline">View</Link>
                    {(v.status === 'ready_for_review' || v.status === 'draft') && (
                      <button onClick={() => handlePublish(v.id)} className="text-green-400 hover:underline">Publish</button>
                    )}
                    <button onClick={() => handleDelete(v.id)} className="text-red-400 hover:underline">Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
