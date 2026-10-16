import { Link, NavLink, Route, Routes, useParams } from 'react-router-dom'
import { api } from '../api'
import { useLoad } from '../ui'
import Teams from './Teams'
import Groups from './Groups'
import MatchPage from './MatchPage'
import LineupPage from './LineupPage'
import Sanctions from './Sanctions'
import Staff from './Staff'
import Bracket from './Bracket'
import Stats from './Stats'
import MyMatches from './MyMatches'

export default function TournamentPage() {
  const tid = Number(useParams().id)
  const { data: t, error } = useLoad(() => api.tournament(tid), [tid])
  const tab = ({ isActive }: { isActive: boolean }) =>
    `flex-1 whitespace-nowrap rounded-lg px-3 py-2 text-center text-sm font-medium ${isActive ? 'bg-green-600 text-white' : 'bg-white text-slate-600 border border-slate-200'}`

  if (!t) return <p className="text-slate-500">{error || 'Cargando…'}</p>
  const admin = t.my_role === 'admin'

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to="/" className="text-sm text-slate-500">← Torneos</Link>
        <h1 className="text-xl font-bold">{t.name}</h1>
        {!admin && <span className="text-xs text-slate-500">Planillero / veedor</span>}
      </div>
      <nav className="flex gap-2 overflow-x-auto">
        {admin ? (
          <NavLink end to={`/t/${tid}`} className={tab}>Equipos</NavLink>
        ) : (
          <NavLink end to={`/t/${tid}`} className={tab}>Mis partidos</NavLink>
        )}
        <NavLink to={`/t/${tid}/grupos`} className={tab}>Grupos y partidos</NavLink>
        <NavLink to={`/t/${tid}/llaves`} className={tab}>Llaves</NavLink>
        <NavLink to={`/t/${tid}/estadisticas`} className={tab}>Estadísticas</NavLink>
        <NavLink to={`/t/${tid}/sanciones`} className={tab}>Sanciones</NavLink>
        {admin && <NavLink to={`/t/${tid}/equipo`} className={tab}>Equipo de trabajo</NavLink>}
      </nav>
      <Routes>
        <Route index element={admin ? <Teams tid={tid} /> : <MyMatches tid={tid} />} />
        <Route path="grupos" element={<Groups tid={tid} admin={admin} />} />
        <Route path="partido/:mid" element={<MatchPage tid={tid} admin={admin} />} />
        <Route path="partido/:mid/buena-fe" element={<LineupPage tid={tid} />} />
        <Route path="llaves" element={<Bracket tid={tid} admin={admin} />} />
        <Route path="estadisticas" element={<Stats tid={tid} admin={admin} />} />
        <Route path="sanciones" element={<Sanctions tid={tid} />} />
        {admin && <Route path="equipo" element={<Staff tid={tid} />} />}
      </Routes>
    </div>
  )
}
