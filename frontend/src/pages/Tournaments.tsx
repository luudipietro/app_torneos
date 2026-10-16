import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { ErrorMsg, useAction, useLoad } from '../ui'

export default function Tournaments() {
  const { data, error, reload } = useLoad(() => api.tournaments(), [])
  const [name, setName] = useState('')
  const [date, setDate] = useState('')
  const act = useAction()

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (await act.run(() => api.createTournament(name, date || null))) { setName(''); setDate(''); reload() }
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={create} className="card flex flex-col gap-3">
        <h2 className="font-semibold">Nuevo torneo</h2>
        <input className="input" placeholder="Nombre del torneo" value={name} onChange={(e) => setName(e.target.value)} required />
        <input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <ErrorMsg msg={act.error} />
        <button className="btn" disabled={act.busy}>Crear torneo</button>
      </form>
      <ErrorMsg msg={error} />
      <ul className="flex flex-col gap-2">
        {data?.map((t) => (
          <li key={t.id}>
            <Link to={`/t/${t.id}`} className="card block active:bg-slate-50">
              <div className="font-semibold">{t.name}</div>
              {t.start_date && <div className="text-sm text-slate-500">Desde {t.start_date}</div>}
            </Link>
          </li>
        ))}
        {data?.length === 0 && <p className="text-center text-slate-500">Todavía no tenés torneos.</p>}
      </ul>
    </div>
  )
}
