import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { fetchBundle } from '../offline/queue'
import { ErrorMsg, useLoad } from '../ui'

const STATUS: Record<string, string> = { scheduled: 'Programado', in_progress: 'En juego', finished: 'Finalizado' }

export default function MyMatches({ tid }: { tid: number }) {
  const matches = useLoad(() => api.myMatches(tid), [tid])
  const teams = useLoad(() => api.teams(tid), [tid])
  // deja guardados en el dispositivo los partidos asignados para poder cargarlos sin señal
  useEffect(() => {
    let alive = true
    ;(async () => {
      for (const m of matches.data ?? []) {
        if (!alive) return
        if (m.status !== 'finished' && m.home_team_id && m.away_team_id) await fetchBundle(m.id).catch(() => {})
      }
    })()
    return () => { alive = false }
  }, [matches.data])
  const name = (id: number | null) => teams.data?.find((t) => t.id === id)?.name ?? 'A definir'

  return (
    <div className="flex flex-col gap-3">
      <ErrorMsg msg={matches.error || teams.error} />
      <ul className="flex flex-col gap-2">
        {matches.data?.map((m) => (
          <li key={m.id}>
            <Link to={`/t/${tid}/partido/${m.id}`} className="card flex items-center justify-between gap-3 active:bg-slate-50">
              <div className="min-w-0">
                <div className="truncate font-semibold">{name(m.home_team_id)} vs {name(m.away_team_id)}</div>
                <div className="text-sm text-slate-500">Fecha {m.round}{m.scheduled_at && ` · ${new Date(m.scheduled_at).toLocaleString('es-AR', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}`}{m.venue && ` · ${m.venue}`}</div>
              </div>
              <div className="text-right text-sm">
                <div className={m.status === 'finished' ? 'text-slate-500' : 'font-semibold text-green-700'}>{STATUS[m.status] ?? m.status}</div>
                {m.home_goals != null && <div className="tabular-nums">{m.home_goals} - {m.away_goals}</div>}
              </div>
            </Link>
          </li>
        ))}
        {matches.data && matches.data.length > 0 && <li className="text-center text-xs text-slate-400">Estos partidos quedan guardados en el dispositivo para usarlos sin conexión.</li>}
        {matches.data?.length === 0 && <li className="card text-center text-slate-500">El organizador todavía no te asignó partidos.</li>}
      </ul>
    </div>
  )
}
