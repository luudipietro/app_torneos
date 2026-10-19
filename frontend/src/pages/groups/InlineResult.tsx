import { useState } from 'react'
import { api, Match } from '../../api'
import { useAction } from '../../ui'

/**
 * Carga rápida del resultado desde la lista (modo prueba). Siempre pide confirmación: al guardar se cierra
 * el partido y el resultado no se puede cambiar (solo el organizador puede reabrirlo desde el partido).
 */
export default function InlineResult({ m, home, away, onSaved }: { m: Match; home: string; away: string; onSaved: () => void }) {
  const [h, setH] = useState('')
  const [a, setA] = useState('')
  const [confirming, setConfirming] = useState(false)
  const act = useAction()
  const box = 'w-14 rounded-lg border border-slate-300 py-1.5 text-center text-base'
  const num = (v: string, set: (s: string) => void, label: string) => (
    <input className={box} inputMode="numeric" aria-label={label} value={v} onChange={(e) => { set(e.target.value.replace(/\D/g, '')); setConfirming(false) }} />
  )
  return (
    <div className="flex w-full flex-col gap-2 pl-8">
      <div className="flex flex-wrap items-center gap-2">
        {num(h, setH, `Goles de ${home}`)}
        <span>-</span>
        {num(a, setA, `Goles de ${away}`)}
        {!confirming && <button className="btn-ghost" disabled={h === '' || a === ''} onClick={() => setConfirming(true)}>Guardar…</button>}
        {act.error && <span className="text-red-600">{act.error}</span>}
      </div>
      {confirming && (
        <div className="flex flex-col gap-2 rounded-lg border-2 border-amber-400 bg-amber-50 p-3" role="alertdialog">
          <p className="font-semibold">¿Confirmás {home} {h} - {a} {away}?</p>
          <p className="text-sm text-amber-900">Se cierra el partido y el resultado no se podrá modificar.</p>
          <div className="flex gap-2">
            <button className="btn" disabled={act.busy} onClick={async () => { if (await act.run(() => api.setResult(m.id, Number(h), Number(a)))) onSaved() }}>Sí, guardar</button>
            <button className="btn-ghost" onClick={() => setConfirming(false)}>Volver</button>
          </div>
        </div>
      )}
    </div>
  )
}
