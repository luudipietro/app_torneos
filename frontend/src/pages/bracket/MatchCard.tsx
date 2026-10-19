import { Link } from 'react-router-dom'
import type { Match } from '../../api'

export type BracketMatch = Pick<Match, 'id' | 'round' | 'home_team_id' | 'away_team_id' | 'home_goals' | 'away_goals' | 'home_pens' | 'away_pens' | 'status' | 'is_third_place'>

export default function MatchCard({ m, names, href }: { m: BracketMatch; names: Map<number, string>; href: string | null }) {
  const done = m.status === 'finished'
  const homeWon = done && (m.home_goals! > m.away_goals! || (m.home_goals === m.away_goals && m.home_pens! > m.away_pens!))
  const row = (id: number | null, goals: number | null, pens: number | null, won: boolean) => (
    <div className={`flex items-center justify-between gap-2 ${done && !won ? 'text-slate-400' : 'font-semibold'}`}>
      <span className="truncate">{id ? names.get(id) : <span className="font-normal italic text-slate-400">A definir</span>}</span>
      <span className="tabular-nums">{goals ?? ''}{pens != null && <span className="ml-1 text-xs font-normal">({pens})</span>}</span>
    </div>
  )
  const body = (
    <div className={`card flex flex-col gap-1 text-sm ${m.status === 'in_progress' ? 'border-green-400' : ''}`}>
      {row(m.home_team_id, m.home_goals, m.home_pens, homeWon)}
      {row(m.away_team_id, m.away_goals, m.away_pens, done && !homeWon)}
    </div>
  )
  return href && m.home_team_id && m.away_team_id ? <Link to={href} className="block active:opacity-70">{body}</Link> : body
}
