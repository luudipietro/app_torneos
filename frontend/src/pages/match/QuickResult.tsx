import { useState } from 'react'
import { api, MatchDetail } from '../../api'
import { ErrorMsg, useAction } from '../../ui'

/**
 * Resultado directo, sin goleadores (requiere conexión): cierra el partido. Pide confirmación porque
 * después no se puede cambiar. Si hay goles cargados como incidencias, el resultado sale de ellos.
 */
export default function QuickResult({ d, home, away, onSaved }: { d: MatchDetail; home: string; away: string; onSaved: () => void }) {
  const [h, setH] = useState('')
  const [a, setA] = useState('')
  const [pens, setPens] = useState({ h: '', a: '' })
  const [confirming, setConfirming] = useState(false)
  const act = useAction()
  const filled = h !== '' && a !== ''
  const tied = d.is_knockout && filled && h === a
  const pensOk = !tied || (pens.h !== '' && pens.a !== '' && pens.h !== pens.a)
  const box = 'w-16 rounded-lg border border-slate-300 py-2 text-center text-base'
  const num = (v: string, set: (s: string) => void, label: string) => (
    <input className={box} inputMode="numeric" aria-label={label} value={v} onChange={(e) => { set(e.target.value.replace(/\D/g, '')); setConfirming(false) }} />
  )
  return (
    <section className="card flex flex-col gap-3">
      <h2 className="font-semibold">Cargar resultado final</h2>
      <p className="text-sm text-slate-500">Para cargar solo el marcador, sin goleadores ni tarjetas (necesita conexión). Si preferís detallar los goles, usá «Cargar incidencia».</p>
      <div className="flex items-center justify-center gap-2">
        <span className="flex-1 truncate text-right text-sm">{home}</span>
        {num(h, setH, `Goles de ${home}`)}
        <span>-</span>
        {num(a, setA, `Goles de ${away}`)}
        <span className="flex-1 truncate text-sm">{away}</span>
      </div>
      {tied && (
        <div className="flex items-center justify-center gap-2 rounded-lg bg-amber-50 p-2 text-sm">
          <span className="text-amber-800">Penales</span>
          {num(pens.h, (v) => setPens({ ...pens, h: v }), 'Penales local')}
          <span>-</span>
          {num(pens.a, (v) => setPens({ ...pens, a: v }), 'Penales visita')}
        </div>
      )}
      <ErrorMsg msg={act.error} />
      {!confirming ? (
        <button className="btn-ghost" disabled={!filled || !pensOk} onClick={() => setConfirming(true)}>Guardar resultado…</button>
      ) : (
        <div className="flex flex-col gap-2 rounded-lg border-2 border-amber-400 bg-amber-50 p-3 text-center" role="alertdialog">
          <p className="font-semibold">¿Confirmás {home} {h} - {a} {away}{tied && ` (penales ${pens.h} - ${pens.a})`}?</p>
          <p className="text-sm text-amber-900">Se cierra el partido y el resultado no se podrá cambiar; solo el organizador puede reabrirlo.</p>
          <div className="flex justify-center gap-2">
            <button className="btn" disabled={act.busy} onClick={async () => {
              if (await act.run(() => api.setResult(d.id, Number(h), Number(a), tied ? { home_pens: Number(pens.h), away_pens: Number(pens.a) } : undefined))) onSaved()
            }}>Sí, guardar</button>
            <button className="btn-ghost" onClick={() => setConfirming(false)}>Volver</button>
          </div>
        </div>
      )}
    </section>
  )
}
