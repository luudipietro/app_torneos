import { Link, useParams } from 'react-router-dom'
import type { Match } from '../../api'
import InlineResult from './InlineResult'

/** Un partido de grupo: solo muestra el estado; el resultado se carga abriendo el partido (con confirmación). */
export default function MatchRow({ m, nm, canEdit, quick, onSaved }: { m: Match; nm: (id: number | null) => string; canEdit: boolean; quick?: boolean; onSaved?: () => void }) {
  const tid = useParams().id
  const done = m.status === 'finished'
  return (
    <li className="flex flex-wrap items-center gap-2 text-sm">
      <span className="w-6 text-xs text-slate-400">F{m.round}</span>
      <span className="flex-1 truncate text-right">{nm(m.home_team_id)}</span>
      <span className={`min-w-16 rounded-lg px-2 py-1.5 text-center text-base font-bold tabular-nums ${done ? 'bg-slate-100' : 'text-slate-400'}`}>
        {m.home_goals != null ? `${m.home_goals} - ${m.away_goals}` : 'vs'}
      </span>
      <span className="flex-1 truncate">{nm(m.away_team_id)}</span>
      {canEdit ? (
        <Link to={`/t/${tid}/partido/${m.id}`} className={`shrink-0 rounded-lg px-3 py-2 text-sm font-semibold ${done ? 'border border-slate-300 text-slate-700' : 'bg-green-600 text-white'}`} title="Goles, tarjetas, planilla y comentarios">
          {done ? 'Ver' : 'Abrir'}
        </Link>
      ) : (
        <span className="text-slate-300" title="No estás asignado a este partido">🔒</span>
      )}
      {quick && canEdit && !done && m.home_team_id && m.away_team_id && (
        <InlineResult m={m} home={nm(m.home_team_id)} away={nm(m.away_team_id)} onSaved={onSaved ?? (() => {})} />
      )}
    </li>
  )
}
