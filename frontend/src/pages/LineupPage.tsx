import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, LineupPlayer, LineupSide, playerPhotoUrl } from '../api'
import { useMatchBundle, useSyncStatus } from '../offline/hooks'
import { ErrorMsg, useAction } from '../ui'

const REASON = { yellows: 'por amarillas', red: 'por expulsión' } as const

export default function LineupPage({ tid }: { tid: number }) {
  const mid = Number(useParams().mid)
  const { view, loading, error, refresh, dispatch } = useMatchBundle(mid)
  const [side, setSide] = useState<'home' | 'away'>('home')
  const act = useAction()
  const [notice, setNotice] = useState('')
  const lu = view?.lineup

  if (!view || !lu) return <ErrorMsg msg={error || (loading ? '' : 'Este partido todavía no tiene los dos equipos definidos')} />
  const closed = view.detail.status === 'finished'
  const s = lu[side]

  const toggle = async (p: LineupPlayer) => {
    setNotice('')
    if (p.present && view.detail.events.some((e) => e.player_id === p.player_id)) {
      setNotice(`${p.name} tiene incidencias cargadas en este partido: borralas antes de sacarlo de la lista.`)
      return
    }
    await dispatch({ kind: p.present ? 'lineup.unmark' : 'lineup.mark', payload: { player_id: p.player_id } })
  }

  return (
    <div className="flex flex-col gap-4">
      <Link to={`/t/${tid}/partido/${mid}`} className="text-sm text-slate-500">← Volver al partido</Link>
      <h1 className="text-xl font-bold">Control de buena fe</h1>
      {closed && <p className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600">Partido cerrado: la lista solo se puede modificar desde la cuenta del organizador.</p>}

      <div className="grid grid-cols-2 gap-2">
        {(['home', 'away'] as const).map((k) => (
          <button key={k} onClick={() => setSide(k)}
            className={`rounded-lg border py-2.5 text-sm font-medium ${side === k ? 'border-green-600 bg-green-50 text-green-800' : 'border-slate-300 bg-white'}`}>
            {lu[k].team_name} <span className="ml-1 rounded-full bg-slate-200 px-2 text-xs">{lu[k].present_count}</span>
          </button>
        ))}
      </div>
      <ErrorMsg msg={act.error || notice} />

      <ul className="flex flex-col gap-2">
        {s.players.map((p) => <PlayerCard key={p.player_id} p={p} locked={closed} onToggle={() => toggle(p)} />)}
        {s.players.length === 0 && <li className="card text-center text-slate-500">Este equipo no tiene jugadores cargados.</li>}
      </ul>

      {!closed && (
        <Onsite side={s} busy={act.busy} onAdd={(d) => act.run(async () => { await api.onsitePlayer(mid, { team_id: s.team_id, ...d }); await refresh() })} />
      )}
    </div>
  )
}

function Avatar({ p }: { p: LineupPlayer }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    if (!p.has_photo) return
    let u = ''
    playerPhotoUrl(p.player_id).then((x) => { u = x; setUrl(x) }).catch(() => setUrl(''))
    return () => { if (u) URL.revokeObjectURL(u) }
  }, [p.player_id, p.has_photo])
  return url
    ? <img src={url} alt={p.name} className="h-16 w-16 rounded-lg object-cover" />
    : <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-slate-100 text-2xl font-bold text-slate-400">{p.number ?? '?'}</div>
}

function PlayerCard({ p, locked, onToggle }: { p: LineupPlayer; locked: boolean; onToggle: () => void }) {
  const blocked = !!p.suspension || !p.enabled
  return (
    <li className={`card flex items-center gap-3 ${blocked ? 'border-red-200 bg-red-50' : p.present ? 'border-green-300 bg-green-50' : ''}`}>
      <Avatar p={p} />
      <div className="min-w-0 flex-1">
        <div className="truncate font-semibold">{p.number != null && <span className="text-slate-400">#{p.number} </span>}{p.name}</div>
        <div className="text-sm text-slate-500">DNI {p.dni}</div>
        {p.suspension && <div className="text-sm font-semibold text-red-700">⛔ Suspendido {REASON[p.suspension.reason]} ({p.suspension.remaining} partido/s)</div>}
        {!p.enabled && <div className="text-sm font-semibold text-red-700">⛔ No habilitado</div>}
        {!blocked && p.yellows > 0 && <div className="text-sm text-amber-700">🟨 {p.yellows} amarilla{p.yellows > 1 ? 's' : ''} acumulada{p.yellows > 1 ? 's' : ''}</div>}
        {p.present && p.verified_by && <div className="text-xs text-green-800">Verificado por {p.verified_by}</div>}
      </div>
      {blocked ? (
        <span className="text-2xl" aria-label="No puede jugar">🚫</span>
      ) : (
        <button disabled={locked} onClick={onToggle}
          className={`h-14 w-24 shrink-0 rounded-xl text-sm font-bold disabled:opacity-50 ${p.present ? 'bg-green-600 text-white' : 'border-2 border-slate-300 bg-white text-slate-600'}`}>
          {p.present ? '✓ Presente' : 'Marcar'}
        </button>
      )}
    </li>
  )
}

function Onsite({ side, busy, onAdd }: { side: LineupSide; busy: boolean; onAdd: (d: { name: string; dni: string; number: number | null }) => Promise<boolean> }) {
  const { online } = useSyncStatus()
  const [open, setOpen] = useState(false)
  const [f, setF] = useState({ name: '', dni: '', number: '' })
  if (!online) return <p className="text-center text-sm text-slate-500">El alta de jugadores en la cancha necesita conexión.</p>
  if (!open) return <button className="btn-ghost" onClick={() => setOpen(true)}>+ Alta de jugador en la cancha</button>
  return (
    <form className="card grid grid-cols-6 gap-2" onSubmit={async (e) => {
      e.preventDefault()
      if (await onAdd({ name: f.name, dni: f.dni, number: f.number ? Number(f.number) : null })) { setF({ name: '', dni: '', number: '' }); setOpen(false) }
    }}>
      <h2 className="col-span-6 font-semibold">Nuevo jugador de {side.team_name}</h2>
      <input className="input col-span-6" placeholder="Nombre y apellido" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
      <input className="input col-span-4" inputMode="numeric" placeholder="DNI" minLength={6} value={f.dni} onChange={(e) => setF({ ...f, dni: e.target.value })} required />
      <input className="input col-span-2" inputMode="numeric" placeholder="N°" value={f.number} onChange={(e) => setF({ ...f, number: e.target.value })} />
      <button type="button" className="btn-ghost col-span-3" onClick={() => setOpen(false)}>Cancelar</button>
      <button className="btn col-span-3" disabled={busy}>Agregar y marcar</button>
    </form>
  )
}
