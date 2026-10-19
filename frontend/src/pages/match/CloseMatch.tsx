import { useState } from 'react'
import type { MatchDetail } from '../../api'

/**
 * Cierre del partido. Pide confirmación avisando que el resultado después no se puede cambiar y,
 * si es de llaves y está empatado (también 0-0), pide los penales.
 */
export default function CloseMatch({ d, home, away, onClose }: {
  d: MatchDetail; home: string; away: string; onClose: (pens?: { home_pens: number; away_pens: number }) => void
}) {
  const [confirming, setConfirming] = useState(false)
  const [pens, setPens] = useState({ h: '', a: '' })
  const hg = d.home_goals ?? 0
  const ag = d.away_goals ?? 0
  const tied = d.is_knockout && hg === ag
  const pensOk = !tied || (pens.h !== '' && pens.a !== '' && pens.h !== pens.a)
  const box = 'w-16 rounded-lg border border-slate-300 py-2 text-center text-base'

  return (
    <div className="flex w-full flex-col gap-2">
      {tied && (
        <div className="flex flex-col items-center gap-2 rounded-lg bg-amber-50 p-3">
          <span className="text-center text-sm font-medium text-amber-800">
            Empate {hg}-{ag} en una llave: se define por penales (también si fue 0-0). Cargá cómo terminaron.
          </span>
          <div className="flex items-center gap-2">
            <input className={box} inputMode="numeric" aria-label={`Penales de ${home}`} placeholder="Local" value={pens.h} onChange={(e) => setPens({ ...pens, h: e.target.value.replace(/\D/g, '') })} />
            <span>-</span>
            <input className={box} inputMode="numeric" aria-label={`Penales de ${away}`} placeholder="Visita" value={pens.a} onChange={(e) => setPens({ ...pens, a: e.target.value.replace(/\D/g, '') })} />
          </div>
          {pens.h !== '' && pens.h === pens.a && <span className="text-sm text-red-600">Los penales no pueden terminar empatados.</span>}
        </div>
      )}
      {!confirming ? (
        <button className="btn" disabled={!pensOk} onClick={() => setConfirming(true)}>Cerrar partido…</button>
      ) : (
        <div className="flex flex-col gap-2 rounded-lg border-2 border-amber-400 bg-amber-50 p-3 text-center" role="alertdialog">
          <p className="font-semibold">¿Confirmás el resultado?</p>
          <p className="text-lg font-bold">
            {home} {hg} - {ag} {away}
            {tied && <span className="block text-sm font-normal">penales {pens.h} - {pens.a}</span>}
          </p>
          <p className="text-sm text-amber-900">Una vez cerrado, el resultado no se puede cambiar: solo el organizador puede reabrir el partido.</p>
          <div className="flex justify-center gap-2">
            <button className="btn" onClick={() => onClose(tied ? { home_pens: Number(pens.h), away_pens: Number(pens.a) } : undefined)}>Sí, cerrar</button>
            <button className="btn-ghost" onClick={() => setConfirming(false)}>Volver</button>
          </div>
        </div>
      )}
    </div>
  )
}
