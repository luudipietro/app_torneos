import { useState } from 'react'
import { useSyncStatus } from './hooks'
import { dismissAllConflicts, dismissConflict, flush } from './queue'
import type { OpKind } from './types'

const LABEL: Record<OpKind, string> = {
  'lineup.mark': 'Marcar presente a un jugador',
  'lineup.unmark': 'Sacar a un jugador de la lista',
  'event.add': 'Gol o tarjeta',
  'event.delete': 'Borrar una incidencia',
  'comment.add': 'Comentario',
  'match.finish': 'Cierre del partido',
  'sheet.upload': 'Foto de la planilla',
}

/** Aviso fijo arriba: sin conexión, cambios pendientes y cambios que el servidor no pudo aplicar. */
export default function SyncBanner() {
  const { online, syncing, pending, conflicts } = useSyncStatus()
  const [open, setOpen] = useState(false)
  if (online && pending === 0 && conflicts.length === 0) return null

  return (
    <div className="sticky top-0 z-10 flex flex-col gap-1 text-sm shadow-sm">
      {!online && (
        <div className="bg-slate-800 px-4 py-2 text-white">
          📴 Sin conexión. Lo que cargues se guarda en este dispositivo y se envía solo cuando vuelva la señal
          {pending > 0 && <b> · {pending} pendiente{pending > 1 ? 's' : ''}</b>}
        </div>
      )}
      {online && pending > 0 && (
        <div className="flex items-center justify-between gap-2 bg-amber-100 px-4 py-2 text-amber-900">
          <span>{syncing ? '🔄 Sincronizando' : '⏳'} {pending} cambio{pending > 1 ? 's' : ''}…</span>
          {!syncing && <button className="font-semibold underline" onClick={() => void flush()}>Reintentar ahora</button>}
        </div>
      )}
      {conflicts.length > 0 && (
        <div className="bg-red-50 px-4 py-2 text-red-900">
          <button className="w-full text-left font-semibold" onClick={() => setOpen(!open)}>
            ⚠️ {conflicts.length} cambio{conflicts.length > 1 ? 's' : ''} no se pudo aplicar {open ? '▲' : '▼'}
          </button>
          {open && (
            <div className="flex flex-col gap-2 pt-2">
              <p className="text-xs">Prevaleció lo que tiene el servidor (por ejemplo, el organizador cerró el partido). Revisá el partido si hace falta.</p>
              {conflicts.map((c) => (
                <div key={c.id} className="flex items-start justify-between gap-2 rounded bg-white p-2">
                  <span><b>{LABEL[c.kind]}</b> · partido {c.matchId}<br /><span className="text-xs">{c.message}</span></span>
                  <button className="shrink-0 text-xs underline" onClick={() => void dismissConflict(c.id!)}>Descartar</button>
                </div>
              ))}
              <button className="self-end text-xs underline" onClick={() => void dismissAllConflicts()}>Descartar todos</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
