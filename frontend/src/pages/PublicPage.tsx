import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { publicApi, PublicData, PublicEvent, PublicMatch } from '../api'
import StatsView from '../components/StatsView'
import { CupBracket } from './Bracket'

type Tab = 'tabla' | 'partidos' | 'llaves' | 'stats'

const ICON: Record<string, string> = { goal: '⚽', penalty_goal: '⚽', own_goal: '🥅', yellow: '🟨', second_yellow: '🟨🟥', red: '🟥' }
const LABEL: Record<string, string> = { penalty_goal: ' (penal)', own_goal: ' (en contra)', second_yellow: ' (doble amarilla)' }
const STATUS: Record<string, string> = { scheduled: 'Por jugar', in_progress: 'En juego', finished: 'Finalizado' }

const when = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('es-AR', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : null

/** Vista pública de solo lectura: se abre con el link o el QR del torneo, sin cuenta. */
export default function PublicPage() {
  const token = useParams().token ?? ''
  const [data, setData] = useState<PublicData | null>(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<Tab>('tabla')

  const load = useCallback(() => {
    publicApi.tournament(token).then((d) => { setData(d); setError('') }).catch((e: Error) => setError(e.message))
  }, [token])

  useEffect(() => {
    load()
    const id = setInterval(() => { if (document.visibilityState === 'visible') load() }, 30000)
    const onVisible = () => { if (document.visibilityState === 'visible') load() }
    document.addEventListener('visibilitychange', onVisible)
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', onVisible) }
  }, [load])

  if (!data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 text-center text-slate-500">
        {error ? <p className="card text-red-700">{error}</p> : 'Cargando…'}
      </div>
    )
  }

  const names = new Map(data.teams.map((t) => [t.id, t.name]))
  const tabs: [Tab, string][] = [['tabla', 'Posiciones'], ['partidos', 'Partidos'], ...(data.cups.length ? [['llaves', 'Llaves'] as [Tab, string]] : []), ['stats', 'Estadísticas']]
  const btn = (active: boolean) => `flex-1 whitespace-nowrap rounded-lg px-3 py-2 text-center text-sm font-medium ${active ? 'bg-green-600 text-white' : 'bg-white text-slate-600 border border-slate-200'}`

  return (
    <div className="mx-auto min-h-screen max-w-3xl px-4 pb-16">
      <header className="py-5">
        <div className="text-sm font-semibold text-green-700">⚽ Torneo de fútbol</div>
        <h1 className="text-2xl font-bold">{data.name}</h1>
        <p className="text-xs text-slate-400">
          Se actualiza solo · {new Date(data.updated_at + 'Z').toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })}
          {error && <span className="ml-2 text-amber-700">Sin conexión: mostrando lo último que se vio</span>}
        </p>
      </header>

      <nav className="mb-4 flex gap-2 overflow-x-auto">
        {tabs.map(([k, label]) => <button key={k} className={btn(tab === k)} onClick={() => setTab(k)}>{label}</button>)}
      </nav>

      {tab === 'tabla' && <Standings data={data} names={names} />}
      {tab === 'partidos' && <Fixture data={data} names={names} token={token} />}
      {tab === 'llaves' && (
        <div className="flex flex-col gap-8">
          {data.cups.map((c) => <CupBracket key={c.name} name={c.name} rounds={c.rounds} matches={c.matches} names={names} hrefFor={() => null} />)}
        </div>
      )}
      {tab === 'stats' && <StatsView stats={data.stats} />}
    </div>
  )
}

function Standings({ data, names }: { data: PublicData; names: Map<number, string> }) {
  if (data.groups.length === 0) return <p className="card text-slate-500">Todavía no se hizo el sorteo de grupos.</p>
  return (
    <div className="flex flex-col gap-4">
      {data.groups.map((g) => (
        <section key={g.id} className="card flex flex-col gap-2">
          <h2 className="font-bold text-green-700">{g.name}</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400">
                  <th className="w-6 font-normal">#</th><th className="font-normal">Equipo</th>
                  {['PJ', 'G', 'E', 'P', 'DG', 'Pts'].map((h) => <th key={h} className="px-1.5 text-right font-normal">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {g.standings.map((r, i) => (
                  <tr key={r.team_id} className="border-t border-slate-100">
                    <td className="py-1.5 text-slate-400">{i + 1}</td>
                    <td className="font-medium">{names.get(r.team_id)}</td>
                    {[r.played, r.won, r.drawn, r.lost, r.gd].map((v, j) => <td key={j} className="px-1.5 text-right tabular-nums">{v}</td>)}
                    <td className="px-1.5 text-right font-bold tabular-nums">{r.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  )
}

function Fixture({ data, names, token }: { data: PublicData; names: Map<number, string>; token: string }) {
  if (data.groups.length === 0) return <p className="card text-slate-500">El fixture se publica después del sorteo.</p>
  return (
    <div className="flex flex-col gap-4">
      {data.groups.map((g) => {
        const rounds = [...new Set(g.matches.map((m) => m.round))].sort((a, b) => a - b)
        return (
          <section key={g.id} className="card flex flex-col gap-3">
            <h2 className="font-bold text-green-700">{g.name}</h2>
            {rounds.map((r) => (
              <div key={r} className="flex flex-col gap-1">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Fecha {r}</h3>
                {g.matches.filter((m) => m.round === r).map((m) => <MatchRow key={m.id} m={m} names={names} token={token} />)}
              </div>
            ))}
          </section>
        )
      })}
    </div>
  )
}

function MatchRow({ m, names, token }: { m: PublicMatch; names: Map<number, string>; token: string }) {
  const [open, setOpen] = useState(false)
  const [events, setEvents] = useState<PublicEvent[] | null>(null)
  const played = m.home_goals != null

  const toggle = () => {
    setOpen(!open)
    if (!events) publicApi.match(token, m.id).then((d) => setEvents(d.events)).catch(() => setEvents([]))
  }
  const date = when(m.scheduled_at)

  return (
    <div className="rounded-lg border border-slate-100">
      <button className="flex w-full flex-col gap-0.5 px-2 py-2 text-left active:bg-slate-50" onClick={toggle}>
        <div className="flex items-center gap-2 text-sm">
          <span className="flex-1 truncate text-right font-medium">{names.get(m.home_team_id ?? 0)}</span>
          <span className={`min-w-14 rounded px-2 py-0.5 text-center font-bold tabular-nums ${played ? 'bg-slate-100' : 'text-slate-300'}`}>
            {played ? `${m.home_goals} - ${m.away_goals}` : 'vs'}
          </span>
          <span className="flex-1 truncate font-medium">{names.get(m.away_team_id ?? 0)}</span>
        </div>
        <div className="text-center text-xs text-slate-400">
          {[date, m.venue, m.status === 'in_progress' ? '🟢 En juego' : !played && !date ? STATUS[m.status] : null].filter(Boolean).join(' · ')}
        </div>
      </button>
      {open && (
        <ul className="flex flex-col gap-1 border-t border-slate-100 px-3 py-2 text-sm">
          {events === null && <li className="text-slate-400">Cargando…</li>}
          {events?.length === 0 && <li className="text-slate-400">Sin goles ni tarjetas registrados.</li>}
          {events?.map((e, i) => (
            <li key={i} className={`flex items-center gap-2 ${e.team_id === m.away_team_id ? 'flex-row-reverse text-right' : ''}`}>
              <span className="w-8 text-slate-400 tabular-nums">{e.minute != null ? `${e.minute}'` : ''}</span>
              <span>{ICON[e.type]}</span>
              <span>{e.player_name}<span className="text-slate-400">{LABEL[e.type] ?? ''}</span></span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
