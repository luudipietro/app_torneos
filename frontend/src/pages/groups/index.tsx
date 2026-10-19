import { api } from '../../api'
import { ErrorMsg, useLoad } from '../../ui'
import DrawBoard from './DrawBoard'
import StageView from './StageView'

export default function Groups({ tid, admin }: { tid: number; admin: boolean }) {
  const me = useLoad(() => api.me(), [])
  const stages = useLoad(() => api.stages(tid), [tid])
  const teams = useLoad(() => api.teams(tid), [tid])
  const stage = stages.data?.[0]

  if (!stages.data || !teams.data) return <ErrorMsg msg={stages.error || teams.error} />
  const names = new Map(teams.data.map((t) => [t.id, t.name]))
  if (!stage && !admin) return <p className="card text-slate-500">El organizador todavía no hizo el sorteo.</p>
  if (!stage) return <DrawBoard tid={tid} teams={teams.data} onDone={stages.reload} />
  return <StageView stage={stage} names={names} onDelete={stages.reload} admin={admin} meId={me.data?.id ?? 0} />
}
