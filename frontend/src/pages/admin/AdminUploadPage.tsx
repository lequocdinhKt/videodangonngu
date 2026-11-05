import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../services/api'
import { LANGUAGES, type LanguageCode, type VideoTranslation } from '../../types'

type FilesByLanguage = Partial<Record<LanguageCode, File>>

const EMPTY_TRANSLATIONS: VideoTranslation[] = LANGUAGES.map(language => ({
  language_code: language.code,
  title: '',
  description: '',
}))

function fileLabel(file?: File) {
  if (!file) return 'Chưa chọn tệp'
  return `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`
}

export default function AdminUploadPage() {
  const navigate = useNavigate()
  const [translations, setTranslations] = useState(EMPTY_TRANSLATIONS)
  const [video, setVideo] = useState<File>()
  const [thumbnail, setThumbnail] = useState<File>()
  const [subtitles, setSubtitles] = useState<FilesByLanguage>({})
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!localStorage.getItem('token')) navigate('/admin/login')
  }, [navigate])

  const totalSteps = useMemo(() => 3 + Object.values(subtitles).filter(Boolean).length, [subtitles])

  const updateTranslation = (code: LanguageCode, field: 'title' | 'description', value: string) => {
    setTranslations(items => items.map(item => item.language_code === code ? { ...item, [field]: value } : item))
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    const viSubtitle = subtitles['vi-VN']
    if (!video || !thumbnail || !viSubtitle) {
      setError('Video MP4, ảnh đại diện và phụ đề tiếng Việt là bắt buộc.')
      return
    }
    if (translations.some(item => !item.title.trim())) {
      setError('Vui lòng nhập tiêu đề cho đủ bốn ngôn ngữ.')
      return
    }

    setLoading(true)
    setError('')
    let completed = 0
    const finishStep = () => { completed += 1; setProgress(Math.round(completed / totalSteps * 100)) }
    try {
      setStatus('Đang tạo bản nháp…')
      const draft = await api.createDraft(translations)
      finishStep()

      setStatus('Đang tải video trực tiếp lên kho lưu trữ…')
      await api.uploadAsset(draft.id, 'video', video, undefined, value => setProgress(Math.round((completed + value / 100) / totalSteps * 100)))
      finishStep()

      setStatus('Đang tải ảnh đại diện…')
      await api.uploadAsset(draft.id, 'thumbnail', thumbnail)
      finishStep()

      for (const language of LANGUAGES) {
        const file = subtitles[language.code]
        if (!file) continue
        setStatus(`Đang nhập phụ đề ${language.nativeLabel}…`)
        await api.uploadAsset(draft.id, 'subtitle', file, language.code)
        finishStep()
      }
      navigate(`/admin/videos/${draft.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tạo video')
    } finally {
      setLoading(false)
      setStatus('')
    }
  }

  return (
    <main className="admin-page">
      <form className="admin-shell" onSubmit={submit}>
        <header className="admin-topbar">
          <div>
            <Link to="/admin" className="muted" style={{ fontSize: 13 }}>← Thư viện nội dung</Link>
            <h1 className="admin-title" style={{ marginTop: 10 }}>Tạo video mới</h1>
            <p className="muted">Video dùng âm thanh gốc tiếng Việt. Hệ thống chỉ xử lý phụ đề.</p>
          </div>
          <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Đang tải lên…' : 'Tạo bản nháp'}</button>
        </header>

        {error && <div className="admin-card danger" role="alert" style={{ marginBottom: 18 }}>{error}</div>}
        {loading && <section className="admin-card" style={{ marginBottom: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><strong>{status}</strong><span>{progress}%</span></div>
          <div className="progress-track" style={{ marginTop: 12 }}><div className="progress-bar" style={{ width: `${progress}%` }} /></div>
          <p className="muted" style={{ marginBottom: 0, fontSize: 13 }}>Không đóng trang cho tới khi hoàn tất. Video lớn được tải thẳng lên R2, không đi qua bộ nhớ API.</p>
        </section>}

        <section className="admin-card" style={{ marginBottom: 18 }}>
          <p className="field-label">NỘI DUNG ĐA NGÔN NGỮ</p>
          <p className="muted">Tiêu đề của cả bốn ngôn ngữ là bắt buộc trước khi xuất bản. Mô tả có thể bổ sung sau.</p>
          <div className="admin-grid two">
            {LANGUAGES.map(language => {
              const translation = translations.find(item => item.language_code === language.code)!
              return <div className="admin-card" key={language.code} style={{ boxShadow: 'none' }}>
                <strong>{language.flag} {language.nativeLabel}</strong>
                <div className="field" style={{ marginTop: 14 }}>
                  <label>Tiêu đề *</label>
                  <input value={translation.title} maxLength={500} onChange={event => updateTranslation(language.code, 'title', event.target.value)} required disabled={loading} />
                </div>
                <div className="field" style={{ marginTop: 12 }}>
                  <label>Mô tả</label>
                  <textarea value={translation.description} maxLength={5000} onChange={event => updateTranslation(language.code, 'description', event.target.value)} disabled={loading} />
                </div>
              </div>
            })}
          </div>
        </section>

        <section className="admin-card" style={{ marginBottom: 18 }}>
          <p className="field-label">TỆP GỐC</p>
          <div className="admin-grid two" style={{ marginTop: 16 }}>
            <label className="file-drop"><input type="file" accept="video/mp4,.mp4" required disabled={loading} onChange={event => setVideo(event.target.files?.[0])} /><span><strong>Video MP4 *</strong><br /><small className="muted">{fileLabel(video)}</small></span></label>
            <label className="file-drop"><input type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp" required disabled={loading} onChange={event => setThumbnail(event.target.files?.[0])} /><span><strong>Ảnh đại diện *</strong><br /><small className="muted">{fileLabel(thumbnail)}</small></span></label>
          </div>
        </section>

        <section className="admin-card">
          <p className="field-label">PHỤ ĐỀ SRT</p>
          <p className="muted">Tiếng Việt bắt buộc. Ba ngôn ngữ còn lại có thể tải ngay hoặc tạo bản dịch nháp bằng Groq ở bước kế tiếp.</p>
          <div className="admin-grid four" style={{ marginTop: 16 }}>
            {LANGUAGES.map(language => <label className="file-drop" key={language.code}>
              <input type="file" accept=".srt,application/x-subrip,text/plain" required={language.code === 'vi-VN'} disabled={loading} onChange={event => setSubtitles(items => ({ ...items, [language.code]: event.target.files?.[0] }))} />
              <span><strong>{language.flag} {language.short.toUpperCase()} {language.code === 'vi-VN' ? '*' : ''}</strong><br /><small className="muted">{fileLabel(subtitles[language.code])}</small></span>
            </label>)}
          </div>
        </section>
      </form>
    </main>
  )
}
