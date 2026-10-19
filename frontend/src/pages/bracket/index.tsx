import { api } from '../../api'
import BulkAssign from '../../components/BulkAssign'
import { ErrorMsg, useAction, useLoad } from '../../ui'
import CupView from './CupView'
import Setup from './Setup'

export default function Bracket({ tid, admin }: { tid: number; admin: boolean }) {
  const stages = useLoad(() => api.stages(tid), [tid])
  const teams = useLoad(() => api.teams(tid), [tid])
  const me = useLoad(() => api.me(), [])
  const cups = (stages.data ?? []).filter((s) => s.type === 'knockout')
  const names = new Map((teams.data ?? []).map((t) => [t.id, t.name]))
  const members = useLoad(() => (admin ? api.members(tid) : Promise.resolve(null)), [tid, admin])
  const act = useAction()

  if (!stages.data || !teams.data) return <ErrorMsg msg={stages.error || teams.error} />
  if (cups.length === 0) {
    if (!admin) return <p className="card text-slate-500">El organizador todavía no armó las llaves.</p>
    const groups = stages.data.find((s) => s.type === 'groups')?.groups ?? []
    return <Setup tid={tid} names={names} maxPosition={Math.max(0, ...groups.map((g) => g.team_ids.length))} onDone={stages.reload} />
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
      {admin && members.data && (
        <details className="card">
          <summary className="cursor-pointer font-semibold">Asignar planilleros y canchas en bloque</summary>
          <div className="pt-3"><BulkAssign tid={tid} people={members.data.members} /></div>
        </details>
      )}
    </div>
  )
}
