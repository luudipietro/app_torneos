import { useState } from 'react'
import { api, Team } from '../api'
import { ErrorMsg, useAction, useLoad } from '../ui'

export default function Teams({ tid }: { tid: number }) {
  const { data: teams, error, reload } = useLoad(() => api.teams(tid), [tid])
  const [name, setName] = useState('')
  const [seed, setSeed] = useState('')
  const [open, setOpen] = useState<number | null>(null)
  const act = useAction()

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    if (await act.run(() => api.createTeam(tid, { name, seed: seed ? Number(seed) : null }))) {
      setName('')
      setSeed('')
      reload()
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={add} className="card flex flex-col gap-3">
        <h2 className="font-semibold">Agregar equipo ({teams?.length ?? 0}/64)</h2>
        <input className="input" placeholder="Nombre del equipo" value={name} onChange={(e) => setName(e.target.value)} required />
        <input className="input" type="number" min={1} placeholder="Cabeza de serie (opcional)" value={seed} onChange={(e) => setSeed(e.target.value)} />
        <p className="text-xs text-slate-500">
          Cabeza de serie: el número es la prioridad (1 = el mejor). En el sorteo los cabezas de serie salen primero y se reparten
          uno por grupo, así no se cruzan entre sí. También podés marcarlos o sacarles la marca después, en la lista.
        </p>
        <ErrorMsg msg={act.error} />
        <button className="btn" disabled={act.busy}>Agregar</button>
      </form>
      <ErrorMsg msg={error} />
      <ul className="flex flex-col gap-2">
        {teams?.map((t) => (
          <li key={t.id} className="card">
            <div className="flex items-center justify-between gap-2">
              <button className="flex-1 text-left font-medium" onClick={() => setOpen(open === t.id ? null : t.id)}>
                {t.name}
              </button>
              <SeedControl team={t} onSaved={reload} />
              <button
                className="text-sm text-red-600"
                onClick={async () => {
                  if (confirm(`¿Borrar ${t.name}?`) && (await act.run(() => api.deleteTeam(t.id)))) reload()
                }}
              >
                Borrar
              </button>
            </div>
            {open === t.id && <Players team={t} />}
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Marca o quita la cabeza de serie de un equipo ya cargado (vacío = sin serie). */
function SeedControl({ team, onSaved }: { team: Team; onSaved: () => void }) {
  const [v, setV] = useState(team.seed?.toString() ?? '')
  const act = useAction()
  const save = async () => {
    const seed = v === '' ? null : Number(v)
    if (seed === team.seed) return
    if (await act.run(() => api.updateTeam(team.id, { seed }))) onSaved()
    else setV(team.seed?.toString() ?? '')
  }
  return (
    <label className="flex items-center gap-1 text-xs text-slate-500" title="Cabeza de serie: 1 = el mejor. Vacío = sin serie.">
      Serie
      <input className="w-14 rounded-lg border border-slate-300 py-1.5 text-center text-sm" inputMode="numeric" placeholder="–" value={v}
        onChange={(e) => setV(e.target.value.replace(/\D/g, ''))} onBlur={save} onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()} />
      {team.seed != null && <button type="button" className="text-red-600" aria-label="Quitar cabeza de serie" onClick={() => { setV(''); act.run(() => api.updateTeam(team.id, { seed: null })).then(onSaved) }}>✕</button>}
    </label>
  )
}

function Players({ team }: { team: Team }) {
  const { data, error, reload } = useLoad(() => api.players(team.id), [team.id])
  const [f, setF] = useState({ name: '', dni: '', number: '' })
  const act = useAction()
  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    const ok = await act.run(() =>
      api.createPlayer(team.id, { name: f.name, dni: f.dni, number: f.number ? Number(f.number) : null }),
    )
    if (ok) {
      setF({ name: '', dni: '', number: '' })
      reload()
    }
  }
  return (
    <div className="mt-3 flex flex-col gap-3 border-t border-slate-100 pt-3">
      <ErrorMsg msg={error} />
      <ul className="flex flex-col gap-1 text-sm">
        {data?.map((p) => (
          <li key={p.id} className="flex items-center justify-between">
            <span>
              <b className="inline-block w-7 text-slate-500">{p.number ?? '–'}</b>
              {p.name} <span className="text-slate-400">· DNI {p.dni}</span>
            </span>
            <span className="flex items-center gap-3">
              <button title={p.enabled ? 'Habilitado (tocar para inhabilitar)' : 'No habilitado (tocar para habilitar)'}
                className={p.enabled ? 'text-green-700' : 'text-red-600'}
                onClick={async () => { await act.run(() => api.setPlayerEnabled(p.id, !p.enabled)); reload() }}>
                {p.enabled ? '✔' : '⛔'}
              </button>
              <label className="cursor-pointer" title="Foto del jugador">
                📷
                <input type="file" accept="image/jpeg,image/png,image/webp" capture="user" className="hidden"
                  onChange={async (e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) { await act.run(() => api.uploadPlayerPhoto(p.id, f)); reload() } }} />
              </label>
              <button className="text-red-600" onClick={async () => { await api.deletePlayer(p.id); reload() }}>✕</button>
            </span>
          </li>
        ))}
        {data?.length === 0 && <li className="text-slate-400">Sin jugadores cargados.</li>}
      </ul>
      <form onSubmit={add} className="grid grid-cols-6 gap-2">
        <input className="input col-span-6" placeholder="Nombre y apellido" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
        <input className="input col-span-3" inputMode="numeric" placeholder="DNI" value={f.dni} onChange={(e) => setF({ ...f, dni: e.target.value })} required minLength={6} />
        <input className="input col-span-1" inputMode="numeric" placeholder="N°" value={f.number} onChange={(e) => setF({ ...f, number: e.target.value })} />
        <button className="btn col-span-2" disabled={act.busy}>Agregar</button>
        <div className="col-span-6">
          <ErrorMsg msg={act.error} />
        </div>
      </form>
    </div>
  )
}
