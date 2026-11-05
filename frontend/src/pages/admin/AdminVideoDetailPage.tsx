import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { adminMediaUrl, api } from '../../services/api'
import { LANGUAGES, type LanguageCode, type PreviewData, type SubtitleCue, type VideoTranslation } from '../../types'

function cueTime(milliseconds: number) {
  const seconds = Math.floor(milliseconds / 1000)
  const ms = milliseconds % 1000
  const minutes = Math.floor(seconds / 60)
  return `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}

export default function AdminVideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [translations, setTranslations] = useState<VideoTranslation[]>([])
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageCode>('vi-VN')
  const [cues, setCues] = useState<SubtitleCue[]>([])
  const [loadingCues, setLoadingCues] = useState(false)
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!id) return
    try {
      const data = await api.preview(id)
      setPreview(data)
      setTranslations(data.translations)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tải được video')
    }
  }, [id])

  useEffect(() => {
    if (!localStorage.getItem('token')) navigate('/admin/login')
    else void load()
  }, [load, navigate])

  useEffect(() => {
    if (preview?.status !== 'processing') return
    const timer = window.setInterval(() => void load(), 2500)
    return () => window.clearInterval(timer)
  }, [load, preview?.status])

  const loadCues = useCallback(async (language: LanguageCode) => {
    if (!id) return
    setSelectedLanguage(language)
    setLoadingCues(true)
    setError('')
    try {
      const track = await api.getSubtitleCues(id, language)
      setCues(track.cues)
    } catch (err) {
      setCues([])
      setError(err instanceof Error ? err.message : 'Chưa có phụ đề cho ngôn ngữ này')
    } finally {
      setLoadingCues(false)
    }
  }, [id])

  useEffect(() => { if (preview) void loadCues(selectedLanguage) }, [preview?.video_id])

  const run = async (label: string, action: () => Promise<unknown>, success: string) => {
    setBusy(label); setError(''); setMessage('')
    try { await action(); setMessage(success); await load() }
    catch (err) { setError(err instanceof Error ? err.message : 'Thao tác thất bại') }
    finally { setBusy('') }
  }

  const updateTranslation = (code: LanguageCode, field: 'title' | 'description', value: string) => {
    setTranslations(items => {
      const exists = items.some(item => item.language_code === code)
      if (!exists) return [...items, { language_code: code, title: field === 'title' ? value : '', description: field === 'description' ? value : '' }]
      return items.map(item => item.language_code === code ? { ...item, [field]: value } : item)
    })
  }

  const replaceSubtitle = async (language: LanguageCode, file?: File) => {
    if (!id || !file) return
    await run('upload', () => api.uploadAsset(id, 'subtitle', file, language), `Đã thay phụ đề ${language}.`)
    await loadCues(language)
  }

  const saveCues = async (approved: boolean) => {
    if (!id) return
    await run('cues', () => api.saveSubtitleCues(id, selectedLanguage, cues, approved), approved ? 'Đã lưu và duyệt phụ đề.' : 'Đã lưu bản nháp phụ đề.')
    await loadCues(selectedLanguage)
  }

  if (!preview) return <main className="admin-page"><div className="state-card">{error || 'Đang tải dữ liệu…'}</div></main>

  const latestJob = [...preview.jobs].reverse().find(job => job.status === 'running' || job.status === 'failed')
  const selectedTrack = preview.languages.find(language => language.language_code === selectedLanguage)

  return (
    <main className="admin-page">
      <div className="admin-shell">
        <header className="admin-topbar">
          <div>
            <Link to="/admin" className="muted" style={{ fontSize: 13 }}>← Thư viện nội dung</Link>
            <h1 className="admin-title" style={{ marginTop: 10 }}>{preview.title || 'Biên tập video'}</h1>
            <span className={`status-pill status-${preview.status}`}>{preview.status.replaceAll('_', ' ')}</span>
          </div>
          <div className="admin-actions">
            {preview.status !== 'published' && <button className="secondary-button" disabled={Boolean(busy) || preview.status === 'processing'} onClick={() => void run('generate', () => api.generate(preview.video_id), 'Đã bắt đầu tạo bản dịch nháp.')}>
              {preview.status === 'processing' ? 'Đang dịch…' : 'Tạo bản dịch nháp'}
            </button>}
            <button className="primary-button" disabled={Boolean(busy)} onClick={() => void run('publish', () => preview.status === 'published' ? api.unpublish(preview.video_id) : api.publish(preview.video_id), preview.status === 'published' ? 'Đã gỡ xuất bản.' : 'Đã xuất bản video.')}>
              {preview.status === 'published' ? 'Gỡ xuất bản' : 'Xuất bản'}
            </button>
          </div>
        </header>

        {error && <div className="admin-card danger" role="alert" style={{ marginBottom: 18 }}>{error}</div>}
        {message && <div className="admin-card success" role="status" style={{ marginBottom: 18 }}>{message}</div>}
        {preview.status === 'processing' && <section className="admin-card" style={{ marginBottom: 18 }}>
          <strong>Đang tạo bản dịch phụ đề nháp</strong>
          <p className="muted">{latestJob?.language_code ? `${latestJob.language_code} · ` : ''}{latestJob?.stage || 'Khởi động'} {latestJob?.progress ?? 0}%</p>
          <div className="progress-track"><div className="progress-bar" style={{ width: `${latestJob?.progress ?? 4}%` }} /></div>
          <p className="muted" style={{ fontSize: 13, marginBottom: 0 }}>Nếu Groq báo giới hạn lượt gọi, bạn có thể thử lại sau hoặc tải SRT thủ công. AI không tự xuất bản.</p>
        </section>}

        <div className="admin-grid two" style={{ alignItems: 'start', marginBottom: 18 }}>
          <section className="admin-card">
            <p className="field-label">XEM TRƯỚC VIDEO GỐC</p>
            {preview.video_url ? <video src={adminMediaUrl(preview.video_url)} controls controlsList="nodownload" onContextMenu={event => event.preventDefault()} style={{ display: 'block', width: '100%', marginTop: 14, borderRadius: 12, background: '#0f172a', aspectRatio: '16/9' }} /> : <div className="state-card" style={{ marginTop: 14 }}>Chưa có video MP4.</div>}
          </section>
          <section className="admin-card">
            <p className="field-label">ĐIỀU KIỆN XUẤT BẢN</p>
            <div className="admin-grid" style={{ marginTop: 14 }}>
              <span>{preview.video_url ? '✓' : '○'} Video MP4</span>
              <span>{preview.thumbnail_url ? '✓' : '○'} Ảnh đại diện</span>
              <span>{LANGUAGES.every(language => translations.some(item => item.language_code === language.code && item.title.trim())) ? '✓' : '○'} Tiêu đề đủ bốn ngôn ngữ</span>
              <span>{preview.languages.filter(language => language.status === 'completed').length}/4 phụ đề đã duyệt</span>
            </div>
          </section>
        </div>

        <section className="admin-card" style={{ marginBottom: 18 }}>
          <div className="admin-topbar" style={{ marginBottom: 18 }}><div><p className="field-label">TIÊU ĐỀ VÀ MÔ TẢ</p><span className="muted">Nội dung hiển thị theo ngôn ngữ người xem chọn.</span></div><button className="secondary-button" disabled={Boolean(busy)} onClick={() => void run('metadata', () => api.updateTranslations(preview.video_id, translations), 'Đã lưu nội dung.')}>Lưu nội dung</button></div>
          <div className="admin-grid two">
            {LANGUAGES.map(language => {
              const item = translations.find(translation => translation.language_code === language.code) || { language_code: language.code, title: '', description: '' }
              return <div className="admin-card" key={language.code} style={{ boxShadow: 'none' }}>
                <strong>{language.flag} {language.nativeLabel}</strong>
                <div className="field" style={{ marginTop: 12 }}><label>Tiêu đề</label><input value={item.title} onChange={event => updateTranslation(language.code, 'title', event.target.value)} /></div>
                <div className="field" style={{ marginTop: 10 }}><label>Mô tả</label><textarea value={item.description} onChange={event => updateTranslation(language.code, 'description', event.target.value)} /></div>
              </div>
            })}
          </div>
        </section>

        <section className="admin-card">
          <div className="admin-topbar" style={{ marginBottom: 18 }}>
            <div><p className="field-label">BIÊN TẬP PHỤ ĐỀ</p><span className="muted">Tải SRT khác để ghi đè, hoặc sửa từng câu rồi duyệt.</span></div>
            <div className="admin-actions"><button className="secondary-button" disabled={Boolean(busy) || cues.length === 0} onClick={() => void saveCues(false)}>Lưu nháp</button><button className="primary-button" disabled={Boolean(busy) || cues.length === 0} onClick={() => void saveCues(true)}>Lưu và duyệt</button></div>
          </div>
          <div className="language-chips" style={{ marginBottom: 16 }}>
            {LANGUAGES.map(language => {
              const track = preview.languages.find(item => item.language_code === language.code)
              return <button key={language.code} className={selectedLanguage === language.code ? 'primary-button' : 'secondary-button'} onClick={() => void loadCues(language.code)}>{language.flag} {language.short.toUpperCase()} · {track?.status || 'pending'}</button>
            })}
          </div>
          <div className="admin-grid two" style={{ alignItems: 'start' }}>
            <div>
              <label className="file-drop">
                <input type="file" accept=".srt,application/x-subrip,text/plain" onChange={event => void replaceSubtitle(selectedLanguage, event.target.files?.[0])} />
                <span><strong>Ghi đè SRT {selectedLanguage}</strong><br /><small className="muted">Timestamp và cấu trúc sẽ được kiểm tra trước khi lưu.</small></span>
              </label>
              {selectedTrack?.subtitle_url && <a className="secondary-button" style={{ display: 'inline-flex', marginTop: 12 }} href={adminMediaUrl(selectedTrack.subtitle_url)} target="_blank" rel="noreferrer">Mở VTT hiện tại</a>}
              {selectedLanguage !== 'vi-VN' && <button className="secondary-button" style={{ margin: '12px 0 0 8px' }} disabled={Boolean(busy)} onClick={() => void run('regenerate', () => api.regenerate(preview.video_id, selectedLanguage), `Đang tạo lại ${selectedLanguage}.`)}>Dịch lại bằng AI</button>}
            </div>
            <div className="cue-list">
              {loadingCues && <p className="muted">Đang tải câu phụ đề…</p>}
              {!loadingCues && cues.length === 0 && <p className="muted">Chưa có câu phụ đề cho ngôn ngữ này.</p>}
              {cues.map((cue, index) => <div className="cue-row" key={`${cue.sequence}-${index}`}>
                <small>#{cue.sequence}<br />{cueTime(cue.start_ms)}<br />{cueTime(cue.end_ms)}</small>
                <textarea value={cue.text} aria-label={`Câu phụ đề ${cue.sequence}`} onChange={event => setCues(items => items.map((item, itemIndex) => itemIndex === index ? { ...item, text: event.target.value } : item))} />
              </div>)}
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}
