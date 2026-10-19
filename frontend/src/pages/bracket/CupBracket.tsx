import MatchCard, { BracketMatch } from './MatchCard'
import { roundName } from './rounds'

/**
 * Árbol de una copa. Solo dibuja: sirve para el organizador y para la vista pública.
 * Si la fase se corta antes de la final (``totalRounds`` > ``rounds``), no hay campeón.
 */
export function CupBracket({ name, rounds, totalRounds = rounds, matches, names, hrefFor }: {
  name: string; rounds: number; totalRounds?: number; matches: BracketMatch[]; names: Map<number, string>
  hrefFor: (m: BracketMatch) => string | null
}) {
  const partial = totalRounds > rounds
  const main = matches.filter((m) => !m.is_third_place)
  const third = matches.find((m) => m.is_third_place)
  const byRound = Array.from({ length: rounds }, (_, i) => main.filter((m) => m.round === i + 1))
  const champ = (() => {
    const f = main.find((m) => m.round === rounds)
    if (partial || !f || f.status !== 'finished') return null
    const homeWon = f.home_goals! > f.away_goals! || (f.home_goals === f.away_goals && f.home_pens! > f.away_pens!)
    return names.get((homeWon ? f.home_team_id : f.away_team_id) ?? 0) ?? null
  })()

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-bold text-green-700">{partial ? '⚔️' : '🏆'} {name}</h2>
      {partial && <p className="text-sm text-slate-500">Fase previa: lo que pase acá define a qué copa va cada equipo.</p>}
      {champ && <p className="rounded-lg bg-amber-50 px-3 py-2 font-semibold text-amber-800">Campeón: {champ}</p>}
      <div className="flex gap-4 overflow-x-auto pb-2">
        {byRound.map((ms, i) => (
          <div key={i} className="flex min-w-60 flex-1 flex-col justify-around gap-3">
            <h3 className="text-center text-xs font-semibold uppercase tracking-wide text-slate-500">{roundName(i + 1, totalRounds)}</h3>
            {ms.map((m) => <MatchCard key={m.id} m={m} names={names} href={hrefFor(m)} />)}
          </div>
        ))}
      </div>
      {third && (
        <div className="max-w-64">
          <h3 className="pb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Tercer puesto</h3>
          <MatchCard m={third} names={names} href={hrefFor(third)} />
        </div>
      )}
    </section>
  )
}

