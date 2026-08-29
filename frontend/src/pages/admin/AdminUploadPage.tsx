import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'

export default function AdminUploadPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [video, setVideo] = useState<File | null>(null)
  const [subtitle, setSubtitle] = useState<File | null>(null)
  const [voice, setVoice] = useState<File | null>(null)
  const [music, setMusic] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!video || !subtitle) { setError('Video and subtitle are required'); return }
    setLoading(true)
    setError('')
    try {
      const form = new FormData()
      form.append('title', title)
      form.append('description', description)
      form.append('video', video)
      form.append('subtitle', subtitle)
      if (voice) form.append('voice', voice)
      if (music) form.append('music', music)
      const result = await api.createVideo(form)
      navigate(`/admin/videos/${result.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen p-4 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Create Video</h1>
      {error && <p className="text-red-400 mb-4">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input type="text" placeholder="Title" value={title} onChange={e => setTitle(e.target.value)} className="w-full bg-gray-900 px-3 py-2 rounded" required />
        <textarea placeholder="Description" value={description} onChange={e => setDescription(e.target.value)} className="w-full bg-gray-900 px-3 py-2 rounded h-24" />
        <label className="block"><span className="text-sm text-gray-400">Video (MP4) *</span><input type="file" accept=".mp4" onChange={e => setVideo(e.target.files?.[0] || null)} className="w-full mt-1" required /></label>
        <label className="block"><span className="text-sm text-gray-400">Subtitle (SRT) *</span><input type="file" accept=".srt" onChange={e => setSubtitle(e.target.files?.[0] || null)} className="w-full mt-1" required /></label>
        <label className="block"><span className="text-sm text-gray-400">Vietnamese Voice (MP3)</span><input type="file" accept=".mp3" onChange={e => setVoice(e.target.files?.[0] || null)} className="w-full mt-1" /></label>
        <label className="block"><span className="text-sm text-gray-400">Background Music (MP3)</span><input type="file" accept=".mp3" onChange={e => setMusic(e.target.files?.[0] || null)} className="w-full mt-1" /></label>
        <button type="submit" disabled={loading} className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold disabled:opacity-50">
          {loading ? 'Uploading...' : 'Create Video'}
        </button>
      </form>
    </div>
  )
}
