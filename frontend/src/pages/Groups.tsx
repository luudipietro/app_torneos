import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, Match, Stage } from '../api'
import { ErrorMsg, useAction, useLoad } from '../ui'

export default function Groups({ tid, admin }: { tid: number; admin: boolean }) {
  const me = useLoad(() => api.me(), [])
  const stages = useLoad(() => api.stages(tid), [tid])
  const teams = useLoad(() => api.teams(tid), [tid])
  const stage = stages.data?.[0]

  if (!stages.data || !teams.data) return <ErrorMsg msg={stages.error || teams.error} />
  const names = new Map(teams.data.map((t) => [t.id, t.name]))
  if (!stage && !admin) return <p className="card text-slate-500">El organizador todavía no hizo el sorteo.</p>
  if (!stage) return <Draw tid={tid} nTeams={teams.data.length} onDone={stages.reload} />
  return <StageView stage={stage} names={names} onDelete={stages.reload} admin={admin} meId={me.data?.id ?? 0} />
}

function Draw({ tid, nTeams, onDone }: { tid: number; nTeams: number; onDone: () => void }) {
  const layouts = useLoad(() => (nTeams >= 4 ? api.layouts(tid) : Promise.resolve([])), [tid, nTeams])
  const [n, setN] = useState(0)
  const [double, setDouble] = useState(false)
  const act = useAction()
  const sel = n || layouts.data?.[0]?.n_groups || 0

  if (nTeams < 4) return <p className="card text-slate-500">Cargá al menos 4 equipos para hacer el sorteo.</p>
  return (
    <div className="card flex flex-col gap-3">
      <h2 className="font-semibold">Sorteo de grupos ({nTeams} equipos)</h2>
      <div className="flex flex-col gap-2">
        {layouts.data?.map((l) => (
          <label
            key={l.n_groups}
            className={`flex items-center gap-3 rounded-lg border p-3 ${sel === l.n_groups ? 'border-green-600 bg-green-50' : 'border-slate-200'}`}
          >
            <input type="radio" checked={sel === l.n_groups} onChange={() => setN(l.n_groups)} />
            <span>
              {l.n_groups} {l.n_groups === 1 ? 'grupo' : 'grupos'} · {l.balanced ? `de ${l.sizes[0]}` : l.sizes.join('/')}
            </span>
          </label>
        ))}
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={double} onChange={(e) => setDouble(e.target.checked)} /> Ida y vuelta
      </label>
      <ErrorMsg msg={layouts.error || act.error} />
      <button
        className="btn"
        disabled={act.busy || !sel}
        onClick={async () => {
          if (await act.run(() => api.createGroups(tid, { n_groups: sel, double_round: double }))) onDone()
        }}
      >
        Sortear y generar fixture
      </button>
    </div>
  )
}

function StageView({ stage, names, onDelete, admin, meId }: { stage: Stage; names: Map<number, string>; onDelete: () => void; admin: boolean; meId: number }) {
  const matches = useLoad(() => api.matches(stage.id), [stage.id])
  const table = useLoad(() => api.standings(stage.id), [stage.id])
  const act = useAction()
  const refresh = () => {
    matches.reload()
    table.reload()
  }
  const nm = (id: number | null) => (id ? (names.get(id) ?? '?') : 'A definir')

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">
          {stage.name} · {names.size} equipos
        </h2>
        {admin && <button
          className="text-sm text-red-600"
          onClick={async () => {
            if (confirm('¿Borrar el sorteo y los partidos?') && (await act.run(() => api.deleteStage(stage.id)))) onDelete()
          }}
        >
          Rehacer sorteo
        </button>}
      </div>
      <ErrorMsg msg={act.error || matches.error || table.error} />
      {stage.groups.map((g) => {
        const rows = table.data?.find((s) => s.group_id === g.id)?.rows ?? []
        const ms = (matches.data ?? []).filter((m) => m.group_id === g.id)
        return (
          <section key={g.id} className="card flex flex-col gap-3">
            <h3 className="font-bold text-green-700">{g.name}</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-400">
                    <th>Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>DG</th><th>Pts</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.team_id} className="border-t border-slate-100">
                      <td className="py-1.5 font-medium">{nm(r.team_id)}</td>
                      <td>{r.played}</td><td>{r.won}</td><td>{r.drawn}</td><td>{r.lost}</td><td>{r.gd}</td>
                      <td className="font-bold">{r.points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="flex flex-col gap-2 border-t border-slate-100 pt-3">
              {ms.map((m) => (
                <MatchRow key={m.id} m={m} nm={nm} onSaved={refresh} canEdit={admin || m.assignee_ids.includes(meId)} />
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

function MatchRow({ m, nm, onSaved, canEdit }: { m: Match; nm: (id: number | null) => string; onSaved: () => void; canEdit: boolean }) {
  const [h, setH] = useState(m.home_goals?.toString() ?? '')
  const [a, setA] = useState(m.away_goals?.toString() ?? '')
  const tid = useParams().id
  const act = useAction()
  const save = async () => {
    const same = h === (m.home_goals?.toString() ?? '') && a === (m.away_goals?.toString() ?? '')
    if (h !== '' && a !== '' && !same && (await act.run(() => api.setResult(m.id, Number(h), Number(a))))) onSaved()
  }
  const box = 'w-12 rounded-lg border border-slate-300 py-2 text-center text-base'
  return (
    <li className="flex items-center gap-2 text-sm">
      <span className="w-6 text-xs text-slate-400">F{m.round}</span>
      <span className="flex-1 truncate text-right">{nm(m.home_team_id)}</span>
      <input className={box} inputMode="numeric" value={h} onChange={(e) => setH(e.target.value.replace(/\D/g, ''))} onBlur={save} disabled={!canEdit} />
      <span>-</span>
      <input className={box} inputMode="numeric" value={a} onChange={(e) => setA(e.target.value.replace(/\D/g, ''))} onBlur={save} disabled={!canEdit} />
      <span className="flex-1 truncate">{nm(m.away_team_id)}</span>
      {canEdit ? (
        <Link to={`/t/${tid}/partido/${m.id}`} className="text-green-700" title="Goles, tarjetas, planilla y comentarios">
          ›
        </Link>
      ) : (
        <span className="text-slate-300" title="No estás asignado a este partido">🔒</span>
      )}
      {act.error && (
        <span className="text-red-600" title={act.error}>
          !
        </span>
      )}
    </li>
  )
}
