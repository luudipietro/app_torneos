import { api, Stage } from '../../api'
import { ErrorMsg, useAction, useLoad, usePersistentState } from '../../ui'
import MatchRow from './MatchRow'

export default function StageView({ stage, names, onDelete, admin, meId }: { stage: Stage; names: Map<number, string>; onDelete: () => void; admin: boolean; meId: number }) {
  const matches = useLoad(() => api.matches(stage.id), [stage.id])
  const table = useLoad(() => api.standings(stage.id), [stage.id])
  const act = useAction()
  const [quick, setQuick] = usePersistentState('quick-results', false)
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
      <label className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
        <input type="checkbox" checked={quick} onChange={(e) => setQuick(e.target.checked)} />
        Modo prueba: cargar resultados desde esta lista (pide confirmación y después no se puede cambiar)
      </label>
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
                <MatchRow key={m.id} m={m} nm={nm} canEdit={admin || m.assignee_ids.includes(meId)} quick={quick}
                  onSaved={() => { matches.reload(); table.reload() }} />
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
