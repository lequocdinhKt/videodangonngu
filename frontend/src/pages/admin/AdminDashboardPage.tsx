import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, formatDate, formatDuration } from '../../services/api'
import type { Video } from '../../types'

interface QRData { url: string; qr_image_base64: string; qr_svg_base64: string }

function downloadDataUrl(dataUrl: string, filename: string) {
  const anchor = document.createElement('a')
  anchor.href = dataUrl
  anchor.download = filename
  anchor.click()
}

export default function AdminDashboardPage() {
  const navigate = useNavigate()
  const [videos, setVideos] = useState<Video[]>([])
  const [qr, setQr] = useState<QRData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [videoData, qrData] = await Promise.all([api.listVideos(), api.getQR()])
      setVideos(videoData.items)
      setQr(qrData)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Không tải được dữ liệu'
      setError(message)
      if (/token|credentials|xác thực|unauthorized/i.test(message)) navigate('/admin/login')
    } finally {
      setLoading(false)
    }
  }, [navigate])

  useEffect(() => {
    if (!localStorage.getItem('token')) navigate('/admin/login')
    else void load()
  }, [load, navigate])

  const changePublishState = async (video: Video) => {
    setError('')
    try {
      if (video.status === 'published') await api.unpublish(video.id)
      else await api.publish(video.id)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không đổi được trạng thái xuất bản')
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Xóa video nháp này? Thao tác không thể hoàn tác.')) return
    try {
      await api.deleteVideo(id)
      setVideos(items => items.filter(video => video.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Xóa video thất bại')
    }
  }

  return (
    <main className="admin-page">
      <div className="admin-shell">
        <header className="admin-topbar">
          <div>
            <p className="eyebrow" style={{ marginTop: 0 }}>VIDEO GUIDE · ADMIN</p>
            <h1 className="admin-title">Thư viện nội dung</h1>
          </div>
          <div className="admin-actions">
            <Link to="/videos" className="secondary-button">Xem trang công khai</Link>
            <Link to="/admin/videos/new" className="primary-button">＋ Thêm video</Link>
            <button className="secondary-button" onClick={() => { localStorage.removeItem('token'); navigate('/admin/login') }}>Đăng xuất</button>
          </div>
        </header>
        {error && <div className="admin-card danger" role="alert" style={{ marginBottom: 18 }}>{error}</div>}
        <div className="admin-grid two" style={{ marginBottom: 22 }}>
          <section className="admin-card">
            <p className="field-label">TỔNG QUAN</p>
            <h2 style={{ margin: '10px 0 4px', fontSize: 34 }}>{videos.length}</h2>
            <p className="muted" style={{ margin: 0 }}>video · {videos.filter(video => video.status === 'published').length} đang xuất bản</p>
          </section>
          {qr && (
            <section className="admin-card qr-card">
              <img src={qr.qr_image_base64} alt="QR chung mở Video Guide" />
              <div>
                <p className="field-label">MÃ QR CHUNG</p>
                <p className="muted" style={{ margin: '7px 0 12px', overflowWrap: 'anywhere' }}>{qr.url}</p>
                <div className="admin-actions">
                  <button className="secondary-button" onClick={() => downloadDataUrl(qr.qr_image_base64, 'video-guide-qr.png')}>Tải PNG</button>
                  <button className="secondary-button" onClick={() => downloadDataUrl(qr.qr_svg_base64, 'video-guide-qr.svg')}>Tải SVG in ấn</button>
                </div>
              </div>
            </section>
          )}
        </div>
        <section className="admin-card">
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Video</th><th>Trạng thái</th><th>Phụ đề</th><th>Thời lượng</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead>
              <tbody>
                {videos.map(video => (
                  <tr key={video.id}>
                    <td><strong>{video.title || 'Chưa có tiêu đề'}</strong><br /><span className="muted">{video.description?.slice(0, 70)}</span></td>
                    <td><span className={`status-pill status-${video.status}`}>{video.status.replaceAll('_', ' ')}</span></td>
                    <td>{video.languages.filter(language => language.status === 'completed').length}/4 đã duyệt</td>
                    <td>{formatDuration(video.duration_ms)}</td>
                    <td>{formatDate(video.created_at)}</td>
                    <td><div className="admin-actions">
                      <Link to={`/admin/videos/${video.id}`} className="secondary-button">Biên tập</Link>
                      <button className="secondary-button" onClick={() => void changePublishState(video)}>{video.status === 'published' ? 'Gỡ xuất bản' : 'Xuất bản'}</button>
                      <button className="secondary-button danger" onClick={() => void handleDelete(video.id)}>Xóa</button>
                    </div></td>
                  </tr>
                ))}
                {!loading && videos.length === 0 && <tr><td colSpan={6} className="muted" style={{ textAlign: 'center', padding: 34 }}>Chưa có video. Hãy tạo nội dung đầu tiên.</td></tr>}
                {loading && <tr><td colSpan={6} className="muted" style={{ textAlign: 'center', padding: 34 }}>Đang tải dữ liệu…</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  )
}
