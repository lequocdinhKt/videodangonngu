import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../services/api'

export default function AdminLoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { access_token } = await api.login(email, password)
      localStorage.setItem('token', access_token)
      navigate('/admin')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Đăng nhập thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="admin-page" style={{ display: 'grid', placeItems: 'center' }}>
      <form onSubmit={handleSubmit} className="admin-card" style={{ width: 'min(420px, 100%)' }}>
        <div className="brand-mark">VG</div>
        <p className="eyebrow">VIDEO GUIDE · ADMIN</p>
        <h1 className="admin-title">Đăng nhập quản trị</h1>
        <p className="muted">Quản lý video, nội dung đa ngôn ngữ và phụ đề.</p>
        <div className="admin-grid" style={{ marginTop: 26 }}>
          <div className="field">
            <label htmlFor="admin-email">Email</label>
            <input id="admin-email" type="email" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="admin-password">Mật khẩu</label>
            <input id="admin-password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required />
          </div>
          {error && <p className="danger" role="alert">{error}</p>}
          <button className="primary-button wide" type="submit" disabled={loading}>{loading ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
          <Link to="/" className="muted" style={{ textAlign: 'center', fontSize: 13 }}>← Về trang người xem</Link>
        </div>
      </form>
    </main>
  )
}
