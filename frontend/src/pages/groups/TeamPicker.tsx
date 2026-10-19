import { groupLetter } from './useDrawAnimation'

/** Elige a qué grupo va un equipo (o lo devuelve al bombo con «Sin grupo»). */
export default function TeamPicker({ value, nGroups, disabled, onChange }: {
  value: number | null; nGroups: number; disabled?: boolean; onChange: (group: number | null) => void
}) {
  return (
    <select
      className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm"
      value={value ?? ''}
      disabled={disabled}
      aria-label="Grupo del equipo"
      onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
    >
      <option value="">Sin grupo</option>
      {Array.from({ length: nGroups }, (_, i) => <option key={i} value={i}>Grupo {groupLetter(i)}</option>)}
    </select>
  )
}
