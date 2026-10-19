import { useState } from 'react'
import { api } from '../api'
import BulkAssign from '../components/BulkAssign'
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
