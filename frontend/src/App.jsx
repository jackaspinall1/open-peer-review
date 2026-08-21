import { Link, Route, Routes, useNavigate } from 'react-router-dom'
import { useMe } from './auth'
import IndexPage from './pages/IndexPage'
import UploadPage from './pages/UploadPage'
import ViewerPage from './pages/ViewerPage'
import LoginPage from './pages/LoginPage'

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
              <span className="username" title={me.orcid}>{me.name}</span>
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
      </Routes>
    </div>
  )
}
