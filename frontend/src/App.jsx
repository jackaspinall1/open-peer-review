import { Link, Route, Routes, useNavigate } from 'react-router-dom'
import { useMe } from './auth'
import IndexPage from './pages/IndexPage'
import AddPaperPage from './pages/UploadPage'
import ViewerPage from './pages/ViewerPage'
import LoginPage from './pages/LoginPage'
import MyPapersPage from './pages/MyPapersPage'
import PrivacyPage from './pages/PrivacyPage'

export default function App() {
  const { me, logout, unread } = useMe()
  const navigate = useNavigate()

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">Open Peer Review</Link>
        <nav>
          <Link to="/upload" className="navlink">Add paper</Link>
          {me?.logged_in ? (
            <span className="userbox">
              <Link to="/me" className="username" title="Your papers and replies">
                {me.name}
                {unread > 0 && <span className="unreaddot" title={`${unread} new repl${unread === 1 ? 'y' : 'ies'}`}>{unread}</span>}
              </Link>
              <button className="linkbtn" onClick={() => logout().then(() => navigate('/'))}>Sign out</button>
            </span>
          ) : (
            <Link to="/login" className="navlink">Sign in</Link>
          )}
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<IndexPage />} />
        <Route path="/upload" element={<AddPaperPage />} />
        <Route path="/doc/:id" element={<ViewerPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/me" element={<MyPapersPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
      </Routes>
      <footer className="sitefoot">
        <span>Open Peer Review · non-commercial, open source (AGPL-3.0)</span>
        <Link to="/privacy">Privacy</Link>
      </footer>
    </div>
  )
}
