import { useEffect, useState, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../services/api'
import type { PreviewData } from '../../types'

export default function AdminVideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [generating, setGenerating] = useState(false)

  const load = useCallback(() => {
    if (!id) return
    api.preview(id).then(setPreview).catch(console.error)
  }, [id])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!preview || preview.status !== 'processing') return
    const interval = setInterval(load, 2000)
    return () => clearInterval(interval)
  }, [preview?.status, load])

  const handleGenerate = async () => {
    if (!id) return
    setGenerating(true)
    await api.generate(id)
    load()
    setGenerating(false)
  }

  const handleRegenerate = async (lang: string) => {
    if (!id) return
    await api.regenerate(id, lang)
    load()
  }

  const handlePublish = async () => {
    if (!id) return
    await api.publish(id)
    load()
  }

  if (!preview) return <div className="p-6 text-center text-gray-400">Loading...</div>

  return (
    <div className="min-h-screen p-4 max-w-4xl mx-auto space-y-6">
      <Link to="/admin" className="text-blue-400 text-sm">← Dashboard</Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Video Detail</h1>
          <p className="text-gray-400">Status: <span className="text-white">{preview.status}</span></p>
        </div>
        <div className="flex gap-2">
          {preview.status !== 'processing' && (
            <button onClick={handleGenerate} disabled={generating} className="px-4 py-2 bg-yellow-600 rounded-lg text-sm font-semibold disabled:opacity-50">
              {generating ? 'Starting...' : 'Generate'}
            </button>
          )}
          {preview.status === 'ready_for_review' && (
            <button onClick={handlePublish} className="px-4 py-2 bg-green-600 rounded-lg text-sm font-semibold">Publish</button>
          )}
        </div>
      </div>

      {preview.video_url && (
        <video src={preview.video_url} controls className="w-full rounded-lg" />
      )}

      <div>
        <h2 className="text-lg font-semibold mb-3">Languages</h2>
        <div className="grid gap-3">
          {preview.languages.map(lang => (
            <div key={lang.language_code} className="bg-gray-900 p-4 rounded-lg flex items-center justify-between">
              <div>
                <span className="font-medium">{lang.language_code}</span>
                <span className={`ml-2 text-xs px-2 py-0.5 rounded ${lang.status === 'completed' ? 'bg-green-800' : 'bg-gray-700'}`}>{lang.status}</span>
                <div className="flex gap-3 mt-1 text-sm text-gray-400">
                  {lang.subtitle_url && <a href={lang.subtitle_url} target="_blank" rel="noreferrer" className="text-blue-400">Subtitle</a>}
                  {lang.audio_url && <a href={lang.audio_url} target="_blank" rel="noreferrer" className="text-blue-400">Audio</a>}
                </div>
              </div>
              {lang.language_code !== 'vi-VN' && (
                <button onClick={() => handleRegenerate(lang.language_code)} className="text-sm text-yellow-400 hover:underline">Regenerate</button>
              )}
            </div>
          ))}
        </div>
      </div>

      {preview.jobs.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Processing Jobs</h2>
          <div className="space-y-2">
            {preview.jobs.map(job => (
              <div key={job.id} className="bg-gray-900 p-3 rounded-lg text-sm flex justify-between">
                <span>{job.stage} {job.language_code && `(${job.language_code})`}</span>
                <span>{job.status} — {job.progress}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
