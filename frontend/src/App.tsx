import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LanguageSelectPage from './pages/public/LanguageSelectPage'
import VideoLibraryPage from './pages/public/VideoLibraryPage'
import VideoDetailPage from './pages/public/VideoDetailPage'
import ChapterOverviewPage from './pages/public/ChapterOverviewPage'
import AdminLoginPage from './pages/admin/AdminLoginPage'
import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminUploadPage from './pages/admin/AdminUploadPage'
import AdminVideoDetailPage from './pages/admin/AdminVideoDetailPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LanguageSelectPage />} />
        <Route path="/videos" element={<VideoLibraryPage />} />
        <Route path="/tong-quan-ma-nhai-ngu-hanh-son" element={<ChapterOverviewPage slug="tong-quan-ma-nhai-ngu-hanh-son" />} />
        <Route path="/giai-ma-ma-nhai" element={<ChapterOverviewPage slug="giai-ma-ma-nhai" />} />
        <Route path="/videos/hoi-an" element={<Navigate to="/videos/tong-quan-ma-nhai-ngu-hanh-son" replace />} />
        <Route path="/videos/ha-long" element={<Navigate to="/videos/giai-ma-ma-nhai" replace />} />
        <Route path="/videos/:id" element={<VideoDetailPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/admin/videos/new" element={<AdminUploadPage />} />
        <Route path="/admin/videos/:id" element={<AdminVideoDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
