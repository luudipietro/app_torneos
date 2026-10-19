import { useState } from 'react'
import { api } from '../../api'
import { ErrorMsg, useAction, useLoad } from '../../ui'

export default function Assignees({ tid, matchId, current }: { tid: number; matchId: number; current: number[] }) {
  const members = useLoad(() => api.members(tid), [tid])
  const [ids, setIds] = useState<number[]>(current)
  const act = useAction()
  const toggle = async (id: number) => {
    const next = ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]
    const prev = ids
    setIds(next)
    if (!(await act.run(() => api.setAssignments(matchId, next)))) setIds(prev)
  }
  return (
    <section className="card flex flex-col gap-2">
      <h2 className="font-semibold">Planilleros asignados</h2>
      {members.data?.members.map((m) => (
        <label key={m.user_id} className="flex items-center gap-3 py-1">
          <input type="checkbox" className="h-5 w-5" checked={ids.includes(m.user_id)} onChange={() => toggle(m.user_id)} />
          <span>{m.name} <span className="text-sm text-slate-400">· {m.role === 'admin' ? 'organizador' : 'planillero'}</span></span>
        </label>
      ))}
      {members.data?.members.length === 1 && <p className="text-sm text-slate-400">Sumá planilleros desde la pestaña «Equipo de trabajo».</p>}
      <ErrorMsg msg={act.error || members.error} />
    </section>
  )
}
