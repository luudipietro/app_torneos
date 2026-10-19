import { useState } from 'react'
import type { LineupPlayer } from '../../api'
import { TYPES } from './constants'

export type Side = { name: string; players: LineupPlayer[] }

export default function EventForm({ sides, onAdd }: { sides: Side[]; onAdd: (p: number, t: string, min: number | null) => Promise<void> }) {
  const [idx, setIdx] = useState(0)
  const [player, setPlayer] = useState('')
  const [type, setType] = useState('goal')
  const [minute, setMinute] = useState('')
  const side = sides[idx]
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onAdd(Number(player), type, minute ? Number(minute) : null)
    setPlayer('')
    setMinute('')
  }
  return (
    <form onSubmit={submit} className="card flex flex-col gap-3">
      <h2 className="font-semibold">Cargar incidencia</h2>
      <div className="grid grid-cols-2 gap-2">
        {sides.map((s, i) => (
          <button type="button" key={s.name} onClick={() => { setIdx(i); setPlayer('') }}
            className={`rounded-lg border py-2.5 text-sm font-medium ${idx === i ? 'border-green-600 bg-green-50 text-green-800' : 'border-slate-300 bg-white'}`}>
            {s.name}
          </button>
        ))}
      </div>
      <select className="input" value={player} onChange={(e) => setPlayer(e.target.value)} required>
        <option value="">Jugador…</option>
        {side.players.map((p) => <option key={p.player_id} value={p.player_id}>{p.number != null ? `#${p.number} ` : ''}{p.name}</option>)}
      </select>
      {side.players.length === 0 && <p className="text-sm text-amber-700">Este equipo no tiene jugadores habilitados.</p>}
      <div className="grid grid-cols-3 gap-2">
        <select className="input col-span-2" value={type} onChange={(e) => setType(e.target.value)}>
          {Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v.icon} {v.label}</option>)}
        </select>
        <input className="input" inputMode="numeric" placeholder="Min." value={minute} onChange={(e) => setMinute(e.target.value.replace(/\D/g, ''))} />
      </div>
      <button className="btn" disabled={!player}>Agregar</button>
    </form>
  )
}
