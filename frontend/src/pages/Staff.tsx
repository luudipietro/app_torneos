import { useState } from 'react'
import { api } from '../api'
import { ErrorMsg, useAction, useLoad } from '../ui'

const ROLE = { admin: 'Organizador', scorer: 'Planillero / veedor' } as const

export default function Staff({ tid }: { tid: number }) {
  const { data, error, reload } = useLoad(() => api.members(tid), [tid])
  const me = useLoad(() => api.me(), [])
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<'scorer' | 'admin'>('scorer')
  const act = useAction()

  const invite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (await act.run(() => api.invite(tid, email, role))) { setEmail(''); reload() }
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={invite} className="card flex flex-col gap-3">
        <h2 className="font-semibold">Sumar planillero, veedor u organizador</h2>
        <p className="text-sm text-slate-500">
          Ingresá el email con el que se registra. Si todavía no tiene cuenta, queda invitado y entra al torneo
          apenas se registre en la app (compartile el link).
        </p>
        <input className="input" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <select className="input" value={role} onChange={(e) => setRole(e.target.value as 'scorer' | 'admin')}>
          <option value="scorer">Planillero / veedor (solo sus partidos)</option>
          <option value="admin">Organizador (acceso total)</option>
        </select>
        <ErrorMsg msg={act.error} />
        <button className="btn" disabled={act.busy}>Invitar</button>
      </form>
      <ErrorMsg msg={error} />

      <section className="flex flex-col gap-2">
        <h2 className="font-semibold">Equipo de trabajo</h2>
        {data?.members.map((m) => (
          <div key={m.user_id} className="card flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="truncate font-medium">{m.name}</div>
              <div className="truncate text-sm text-slate-500">{m.email} · {ROLE[m.role]}</div>
            </div>
            {m.user_id !== me.data?.id && (
              <button className="text-sm text-red-600" onClick={async () => {
                if (confirm(`¿Sacar a ${m.name} del torneo?`) && (await act.run(() => api.removeMember(tid, m.user_id)))) reload()
              }}>Quitar</button>
            )}
          </div>
        ))}
        {data?.invitations.map((i) => (
          <div key={i.id} className="card flex items-center justify-between gap-2 border-dashed">
            <div className="min-w-0">
              <div className="truncate font-medium text-slate-600">{i.email}</div>
              <div className="text-sm text-amber-700">Invitación pendiente · {ROLE[i.role]}</div>
            </div>
            <button className="text-sm text-red-600" onClick={async () => { if (await act.run(() => api.cancelInvitation(tid, i.id))) reload() }}>Cancelar</button>
          </div>
        ))}
      </section>

      {data && <BulkAssign tid={tid} people={data.members} />}
    </div>
  )
}

function BulkAssign({ tid, people }: { tid: number; people: { user_id: number; name: string }[] }) {
  const stage = useLoad(() => api.stages(tid).then((s) => s[0] ?? null), [tid])
  const matches = useLoad(() => (stage.data ? api.matches(stage.data.id) : Promise.resolve([])), [stage.data?.id])
  const [person, setPerson] = useState('')
  const [round, setRound] = useState('')
  const [group, setGroup] = useState('')
  const [done, setDone] = useState('')
  const act = useAction()
  if (!stage.data) return null
  const rounds = [...new Set((matches.data ?? []).map((m) => m.round))].sort((a, b) => a - b)

  const assign = async () => {
    const ids = (matches.data ?? [])
      .filter((m) => (!round || m.round === Number(round)) && (!group || m.group_id === Number(group)))
      .map((m) => m.id)
    setDone('')
    if (ids.length && (await act.run(() => api.bulkAssign(tid, Number(person), ids)))) {
      setDone(`Asignado a ${ids.length} partido${ids.length > 1 ? 's' : ''}.`)
      matches.reload()
    }
  }

  return (
    <section className="card flex flex-col gap-3">
      <h2 className="font-semibold">Asignar partidos en bloque</h2>
      <p className="text-sm text-slate-500">También podés asignar uno por uno desde la pantalla de cada partido.</p>
      <select className="input" value={person} onChange={(e) => setPerson(e.target.value)}>
        <option value="">Persona…</option>
        {people.map((p) => <option key={p.user_id} value={p.user_id}>{p.name}</option>)}
      </select>
      <div className="grid grid-cols-2 gap-2">
        <select className="input" value={round} onChange={(e) => setRound(e.target.value)}>
          <option value="">Todas las fechas</option>
          {rounds.map((r) => <option key={r} value={r}>Fecha {r}</option>)}
        </select>
        <select className="input" value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">Todos los grupos</option>
          {stage.data.groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
      </div>
      <ErrorMsg msg={act.error} />
      {done && <p className="rounded-lg bg-green-50 px-3 py-2 text-sm text-green-800">{done}</p>}
      <button className="btn" disabled={!person || act.busy} onClick={assign}>Asignar</button>
    </section>
  )
}
