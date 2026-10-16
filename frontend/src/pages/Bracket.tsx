import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, KnockoutPreview, Match, Plan, Stage } from '../api'
import { ErrorMsg, useAction, useLoad } from '../ui'

const ROUND_NAMES = ['Final', 'Semifinales', 'Cuartos de final', 'Octavos de final', 'Dieciseisavos de final']
const roundName = (round: number, rounds: number) => {
  const left = rounds - round
  return ROUND_NAMES[left] ?? `Ronda de ${2 ** (left + 1)}`
}

export default function Bracket({ tid, admin }: { tid: number; admin: boolean }) {
  const stages = useLoad(() => api.stages(tid), [tid])
  const teams = useLoad(() => api.teams(tid), [tid])
  const me = useLoad(() => api.me(), [])
  const cups = (stages.data ?? []).filter((s) => s.type === 'knockout')
  const names = new Map((teams.data ?? []).map((t) => [t.id, t.name]))
  const act = useAction()

  if (!stages.data || !teams.data) return <ErrorMsg msg={stages.error || teams.error} />
  if (cups.length === 0) {
    if (!admin) return <p className="card text-slate-500">El organizador todavía no armó las llaves.</p>
    return <Setup tid={tid} names={names} onDone={stages.reload} />
  }
  return (
    <div className="flex flex-col gap-6">
      {admin && (
        <button className="self-end text-sm text-red-600" onClick={async () => {
          if (!confirm('¿Borrar las llaves para rehacerlas?')) return
          if (await act.run(async () => { for (const c of cups) await api.deleteStage(c.id) })) stages.reload()
        }}>Rehacer llaves</button>
      )}
      <ErrorMsg msg={act.error} />
      {cups.map((c) => <CupView key={c.id} stage={c} names={names} tid={tid} admin={admin} meId={me.data?.id ?? 0} />)}
    </div>
  )
}

function Setup({ tid, names, onDone }: { tid: number; names: Map<number, string>; onDone: () => void }) {
  const plans = useLoad(() => api.knockoutPlans(tid), [tid])
  const [idx, setIdx] = useState(0)
  const [third, setThird] = useState(true)
  const [avoid, setAvoid] = useState(true)
  const [preview, setPreview] = useState<KnockoutPreview | null>(null)
  const act = useAction()
  const plan: Plan | undefined = plans.data?.[idx]

  useEffect(() => {
    if (!plan) return
    setPreview(null)
    act.run(async () => setPreview(await api.knockoutPreview(tid, { cups: plan.cups, third_place: third, avoid_same_group: avoid })))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan, third, avoid])

  if (!plans.data) return <ErrorMsg msg={plans.error} />
  if (plans.data.length === 0) return <p className="card text-slate-500">No hay formatos sugeridos para esta cantidad de grupos.</p>

  return (
    <div className="flex flex-col gap-4">
      <section className="card flex flex-col gap-3">
        <h2 className="font-semibold">Clasificación a las llaves</h2>
        <div className="flex flex-col gap-2">
          {plans.data.map((p, i) => (
            <label key={p.label} className={`flex items-center gap-3 rounded-lg border p-3 text-sm ${idx === i ? 'border-green-600 bg-green-50' : 'border-slate-200'}`}>
              <input type="radio" checked={idx === i} onChange={() => setIdx(i)} />
              <span>{p.label}</span>
            </label>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={third} onChange={(e) => setThird(e.target.checked)} /> Partido por el 3er puesto</label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={avoid} onChange={(e) => setAvoid(e.target.checked)} /> Evitar cruces entre equipos del mismo grupo</label>
      </section>

      <ErrorMsg msg={act.error} />
      {preview && (
        <>
          {preview.unplayed > 0 && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Faltan cerrar {preview.unplayed} partidos de la fase de grupos. Lo que ves es provisorio.
            </p>
          )}
          {preview.cups.map((c) => (
            <section key={c.name} className="card flex flex-col gap-2">
              <h3 className="font-bold text-green-700">{c.name}</h3>
              <p className="text-sm text-slate-500">
                {c.entrants.length} equipos · llave de {c.size}{c.byes > 0 && ` · ${c.byes} pasan directo (bye)`}
              </p>
              <ol className="flex flex-col gap-1 text-sm">
                {c.entrants.map((e) => (
                  <li key={e.team_id} className="flex items-center gap-2">
                    <span className="w-7 text-right text-slate-400">{e.seed}</span>
                    <span className="flex-1 truncate">{names.get(e.team_id)}</span>
                    <span className="text-slate-400">{e.position}º {e.group_name.replace('Grupo ', '')}</span>
                    <span className="w-14 text-right tabular-nums text-slate-500">{e.points} pts</span>
                  </li>
                ))}
              </ol>
            </section>
          ))}
          <button className="btn" disabled={act.busy || preview.unplayed > 0 || !plan}
            onClick={async () => { if (plan && (await act.run(() => api.createKnockout(tid, { cups: plan.cups, third_place: third, avoid_same_group: avoid })))) onDone() }}>
            Crear llaves
          </button>
        </>
      )}
    </div>
  )
}

function CupView({ stage, names, tid, admin, meId }: { stage: Stage; names: Map<number, string>; tid: number; admin: boolean; meId: number }) {
  const matches = useLoad(() => api.matches(stage.id), [stage.id])
  return (
    <>
      <ErrorMsg msg={matches.error} />
      <CupBracket
        name={stage.name}
        rounds={Number(stage.config.rounds ?? 1)}
        matches={matches.data ?? []}
        names={names}
        hrefFor={(m) => ((admin || (m as Match).assignee_ids?.includes(meId)) ? `/t/${tid}/partido/${m.id}` : null)}
      />
    </>
  )
}

type BracketMatch = Pick<Match, 'id' | 'round' | 'home_team_id' | 'away_team_id' | 'home_goals' | 'away_goals' | 'home_pens' | 'away_pens' | 'status' | 'is_third_place'>

/** Árbol de una copa. Solo dibuja: sirve para el organizador y para la vista pública. */
export function CupBracket({ name, rounds, matches, names, hrefFor }: {
  name: string; rounds: number; matches: BracketMatch[]; names: Map<number, string>; hrefFor: (m: BracketMatch) => string | null
}) {
  const main = matches.filter((m) => !m.is_third_place)
  const third = matches.find((m) => m.is_third_place)
  const byRound = Array.from({ length: rounds }, (_, i) => main.filter((m) => m.round === i + 1))
  const champ = (() => {
    const f = main.find((m) => m.round === rounds)
    if (!f || f.status !== 'finished') return null
    const homeWon = f.home_goals! > f.away_goals! || (f.home_goals === f.away_goals && f.home_pens! > f.away_pens!)
    return names.get((homeWon ? f.home_team_id : f.away_team_id) ?? 0) ?? null
  })()

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-bold text-green-700">🏆 {name}</h2>
      {champ && <p className="rounded-lg bg-amber-50 px-3 py-2 font-semibold text-amber-800">Campeón: {champ}</p>}
      <div className="flex gap-4 overflow-x-auto pb-2">
        {byRound.map((ms, i) => (
          <div key={i} className="flex min-w-60 flex-1 flex-col justify-around gap-3">
            <h3 className="text-center text-xs font-semibold uppercase tracking-wide text-slate-500">{roundName(i + 1, rounds)}</h3>
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

function MatchCard({ m, names, href }: { m: BracketMatch; names: Map<number, string>; href: string | null }) {
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
