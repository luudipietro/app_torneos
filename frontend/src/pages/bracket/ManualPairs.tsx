import type { Entrant, Pair } from '../../api'

/** Elegir a mano cada cruce de la primera ronda (el orden de la lista es el de la llave). */
export default function ManualPairs({ entrants, current, seeded, names, onChange }: {
  entrants: Entrant[]; current: [string, string][]; seeded: Pair[]; names: Map<number, string>
  onChange: (pairs: [string, string][]) => void
}) {
  const rows = Math.floor(entrants.length / 2)
  const label = (e: Entrant) => `${e.code} · ${e.team_id != null ? names.get(e.team_id) : e.label}`
  const value = (i: number, side: 0 | 1) => current[i]?.[side] ?? ''
  const set = (i: number, side: 0 | 1, code: string) => {
    const next = Array.from({ length: rows }, (_, j) => (current[j] ?? ['', '']).slice() as [string, string])
    next[i][side] = code
    onChange(next)
  }
  const used = new Set(current.flat())
  if (entrants.length < 2 || entrants.length % 2 || (entrants.length & (entrants.length - 1)) !== 0)
    return <p className="text-sm text-amber-700">Los cruces manuales necesitan una cantidad de equipos potencia de 2 (hay {entrants.length}).</p>
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">Cruces de la primera ronda</span>
        <button className="text-sm text-green-700" onClick={() => onChange(seeded.map((p) => [p.home.code, p.away.code]))}>
          Cargar los cruces por siembra
        </button>
      </div>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span className="w-5 text-slate-400">{i + 1}</span>
          {([0, 1] as const).map((side) => (
            <span key={side} className="contents">
              {side === 1 && <span className="text-slate-400">vs</span>}
              <select className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-2 py-2" value={value(i, side)} onChange={(e) => set(i, side, e.target.value)}>
                <option value="">Elegir…</option>
                {entrants.map((e) => (
                  <option key={e.code} value={e.code} disabled={used.has(e.code) && value(i, side) !== e.code}>{label(e)}</option>
                ))}
              </select>
            </span>
          ))}
        </div>
      ))}
    </div>
  )
}
