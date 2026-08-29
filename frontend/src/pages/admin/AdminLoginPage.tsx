import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'

export default function AdminLoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const { access_token } = await api.login(email, password)
      localStorage.setItem('token', access_token)
      navigate('/admin')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm bg-gray-900 p-6 rounded-xl space-y-4">
        <h1 className="text-xl font-bold">Admin Login</h1>
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" className="w-full bg-gray-800 px-3 py-2 rounded" required />
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" className="w-full bg-gray-800 px-3 py-2 rounded" required />
        <button type="submit" className="w-full py-2 bg-blue-600 hover:bg-blue-500 rounded font-semibold">Login</button>
      </form>
    </div>
  )
}
