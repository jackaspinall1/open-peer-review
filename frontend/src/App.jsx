import { Link, Route, Routes, useNavigate } from 'react-router-dom'
import { useMe } from './auth'
import IndexPage from './pages/IndexPage'
import UploadPage from './pages/UploadPage'
import ViewerPage from './pages/ViewerPage'
import LoginPage from './pages/LoginPage'
import MyPapersPage from './pages/MyPapersPage'

export default function App() {
  const { me, logout } = useMe()
  const navigate = useNavigate()

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">Open Peer Review</Link>
        <nav>
          <Link to="/upload" className="navlink">Upload paper</Link>
          {me?.logged_in ? (
            <span className="userbox">
              <Link to="/me" className="username" title="Your papers">{me.name}</Link>
              <button className="linkbtn" onClick={() => logout().then(() => navigate('/'))}>Sign out</button>
            </span>
          ) : (
            <Link to="/login" className="navlink">Sign in</Link>
          )}
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<IndexPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/doc/:id" element={<ViewerPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/me" element={<MyPapersPage />} />
      </Routes>
    </div>
  )
}
