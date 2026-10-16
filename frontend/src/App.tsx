import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { api, getToken, setToken } from './api'
import SyncBanner from './offline/SyncBanner'
import { clearPrivateData } from './offline/cache'
import { flush, getMe, pendingOps, setMe, startSync } from './offline/queue'
import Login from './pages/Login'
import PublicPage from './pages/PublicPage'
import Tournaments from './pages/Tournaments'
import TournamentPage from './pages/TournamentPage'

async function logout(nav: (to: string) => void) {
  const n = (await pendingOps()).length
  if (n > 0 && !confirm(`Hay ${n} cambio${n > 1 ? 's' : ''} sin sincronizar en este dispositivo. Se enviarán la próxima vez que ingreses con esta cuenta. ¿Salir igual?`)) return
  setToken(null)
  setMe(null)
  await clearPrivateData() // copias de partidos y respuestas guardadas; la cola pendiente se conserva
  nav('/login')
}

function Protected({ children }: { children: React.ReactNode }) {
  const nav = useNavigate()
  const authed = !!getToken()
  useEffect(() => {
    if (!authed) return
    startSync()
    if (!getMe()) api.me().then((u) => { setMe({ id: u.id, name: u.name }); void flush() }).catch(() => {})
  }, [authed])
  if (!authed) return <Navigate to="/login" replace />
  return (
    <>
      <SyncBanner />
      <div className="mx-auto min-h-screen max-w-3xl px-4 pb-16">
        <header className="flex items-center justify-between py-4">
          <Link to="/" className="text-lg font-bold text-green-700">⚽ Torneos</Link>
          <button className="text-sm text-slate-500" onClick={() => void logout(nav)}>Salir</button>
        </header>
        {children}
      </div>
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/p/:token" element={<PublicPage />} />
      <Route path="/" element={<Protected><Tournaments /></Protected>} />
      <Route path="/t/:id/*" element={<Protected><TournamentPage /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
