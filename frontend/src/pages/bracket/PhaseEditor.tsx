import type { Cup, Entrant, Pair, Pairing } from '../../api'
import ManualPairs from './ManualPairs'

const PAIRINGS: [Pairing, string][] = [
  ['seeded', 'Por siembra: mejor contra peor'],
  ['cross', 'Cruzado estilo mundial (1ºA-2ºB, 1ºB-2ºA)'],
  ['random', 'Al azar'],
  ['manual', 'Manual: elijo cada cruce'],
]
const newSeed = () => Math.floor(Math.random() * 1_000_000)
const ordinal = (n: number) => `${n}º`
const TRI = [['', 'Según la opción general'], ['yes', 'Sí'], ['no', 'No']] as const
const toTri = (v: boolean | null | undefined) => (v == null ? '' : v ? 'yes' : 'no')
const fromTri = (v: string) => (v === '' ? null : v === 'yes')

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} /> {label}
    </label>
  )
}

const toggle = <T,>(list: T[], v: T, on: boolean) => (on ? [...list, v] : list.filter((x) => x !== v))

/**
 * Editor de una copa o fase: quiénes entran (puestos de grupo, mejores N de un puesto, ganadores o
 * perdedores de fases anteriores) y cómo se juega (rondas, 3er puesto, cruces del mismo grupo).
 */
export default function PhaseEditor({ cup, others, maxPosition, entrants, seeded, names, onChange, onRemove, onMove }: {
  cup: Cup; others: string[]; maxPosition: number
  entrants?: Entrant[]; seeded: Pair[]; names: Map<number, string>
  onChange: (patch: Partial<Cup>) => void; onRemove: () => void; onMove: (dir: -1 | 1) => void
}) {
  const positions = Array.from({ length: maxPosition }, (_, i) => i + 1)
  const extra = cup.extra ?? []
  const winners = cup.from_winners ?? []
  const losers = cup.from_losers ?? []
  return (
    <div className="flex flex-col gap-3 border-t border-slate-100 pt-3">
      <label className="flex flex-col gap-1 text-sm font-medium">
        Nombre
        <input className="input" value={cup.name} maxLength={120} onChange={(e) => onChange({ name: e.target.value })} />
      </label>

      <fieldset className="flex flex-col gap-1.5">
        <legend className="pb-1 text-sm font-medium">Entran los equipos que terminaron…</legend>
        <div className="flex flex-wrap gap-2">
          {positions.map((p) => (
            <Check key={p} label={`${ordinal(p)} del grupo`} checked={cup.positions.includes(p)}
              onChange={(on) => onChange({ positions: toggle(cup.positions, p, on).sort((a, b) => a - b) })} />
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-1.5">
        <legend className="pb-1 text-sm font-medium">…más los mejores de un puesto (entre todos los grupos)</legend>
        {extra.map((x, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span>Los</span>
            <input className="w-16 rounded-lg border border-slate-300 py-2 text-center" inputMode="numeric" value={x.count}
              onChange={(e) => onChange({ extra: extra.map((y, j) => (j === i ? { ...y, count: Number(e.target.value.replace(/\D/g, '')) || 1 } : y)) })} />
            <span>mejores</span>
            <select className="rounded-lg border border-slate-300 bg-white px-2 py-2" value={x.position}
              onChange={(e) => onChange({ extra: extra.map((y, j) => (j === i ? { ...y, position: Number(e.target.value) } : y)) })}>
              {positions.map((p) => <option key={p} value={p}>{ordinal(p)}</option>)}
            </select>
            <button className="text-red-600" aria-label="Quitar" onClick={() => onChange({ extra: extra.filter((_, j) => j !== i) })}>✕</button>
          </div>
        ))}
        <button className="self-start text-sm text-green-700" onClick={() => onChange({ extra: [...extra, { position: Math.min(2, maxPosition) || 1, count: 2 }] })}>
          + Agregar «los mejores N»
        </button>
      </fieldset>

      {others.length > 0 && (
        <>
          <fieldset className="flex flex-col gap-1.5">
            <legend className="pb-1 text-sm font-medium">Suben los ganadores de…</legend>
            <div className="flex flex-wrap gap-2">
              {others.map((n) => <Check key={n} label={n} checked={winners.includes(n)} onChange={(on) => onChange({ from_winners: toggle(winners, n, on) })} />)}
            </div>
          </fieldset>
          <fieldset className="flex flex-col gap-1.5">
            <legend className="pb-1 text-sm font-medium">Entran los perdedores de…</legend>
            <div className="flex flex-wrap gap-2">
              {others.map((n) => <Check key={n} label={n} checked={losers.includes(n)} onChange={(on) => onChange({ from_losers: toggle(losers, n, on) })} />)}
            </div>
          </fieldset>
        </>
      )}

      <div className="flex flex-col gap-2">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Cómo se arman los cruces
          <select className="input" value={cup.pairing ?? 'seeded'}
            onChange={(e) => onChange({ pairing: e.target.value as Pairing, ...(e.target.value === 'random' && cup.pairing_seed == null ? { pairing_seed: newSeed() } : {}) })}>
            {PAIRINGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        {cup.pairing === 'random' && (
          <button className="self-start text-sm text-green-700" onClick={() => onChange({ pairing_seed: newSeed() })}>🎲 Sortear de nuevo los cruces</button>
        )}
        {cup.pairing === 'cross' && (
          <p className="text-sm text-slate-500">Primero de un grupo contra segundo del grupo vecino (1ºA-2ºB, 1ºB-2ºA). Usa solo 1º y 2º de cada grupo.</p>
        )}
        {cup.pairing === 'manual' && (entrants
          ? <ManualPairs entrants={entrants} current={cup.manual_pairs ?? []} seeded={seeded} names={names} onChange={(p) => onChange({ manual_pairs: p })} />
          : <p className="text-sm text-slate-500">Elegí primero quiénes entran a esta copa.</p>)}
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Rondas a jugar
          <select className="input" value={cup.max_rounds ?? ''} onChange={(e) => onChange({ max_rounds: e.target.value ? Number(e.target.value) : null })}>
            <option value="">Llave completa</option>
            <option value="1">Solo 1 ronda</option>
            <option value="2">Solo 2 rondas</option>
            <option value="3">Solo 3 rondas</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Partido por el 3er puesto
          <select className="input" value={toTri(cup.third_place)} onChange={(e) => onChange({ third_place: fromTri(e.target.value) })}>
            {TRI.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Evitar cruces del mismo grupo
          <select className="input" value={toTri(cup.avoid_same_group)} onChange={(e) => onChange({ avoid_same_group: fromTri(e.target.value) })}>
            {TRI.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
      </div>
      {(cup.max_rounds ?? 0) > 0 && (
        <p className="text-sm text-slate-500">
          Con rondas limitadas la fase termina ahí: los ganadores y perdedores de la última ronda pueden pasar a otras copas.
        </p>
      )}

      <div className="flex justify-between text-sm">
        <span className="flex gap-3">
          <button className="text-slate-600" onClick={() => onMove(-1)}>↑ Subir</button>
          <button className="text-slate-600" onClick={() => onMove(1)}>↓ Bajar</button>
        </span>
        <button className="text-red-600" onClick={onRemove}>Quitar esta copa</button>
      </div>
    </div>
  )
}
