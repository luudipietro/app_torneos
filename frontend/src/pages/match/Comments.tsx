import { useState } from 'react'
import type { MatchDetail } from '../../api'
import { Pending } from './constants'

export default function Comments({ d, onAdd, onDelete }: { d: MatchDetail; onAdd: (t: string) => Promise<void>; onDelete: (id: number) => Promise<unknown> }) {
  const [text, setText] = useState('')
  return (
    <section className="card flex flex-col gap-3">
      <h2 className="font-semibold">Comentarios</h2>
      <ul className="flex flex-col gap-2 text-sm">
        {d.comments.map((c) => (
          <li key={c.id} className="rounded-lg bg-slate-50 p-2.5">
            <div className="flex justify-between text-xs text-slate-500">
              <span>{c.author} · {new Date(c.created_at + 'Z').toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })}{c.pending && <Pending />}</span>
              {!c.pending && <button className="text-red-600" onClick={() => onDelete(c.id)}>Borrar</button>}
            </div>
            <p className="whitespace-pre-wrap pt-1">{c.text}</p>
          </li>
        ))}
        {d.comments.length === 0 && <li className="text-slate-400">Sin comentarios.</li>}
      </ul>
      <form className="flex gap-2" onSubmit={async (e) => { e.preventDefault(); if (text.trim()) { const t = text.trim(); setText(''); await onAdd(t) } }}>
        <input className="input" placeholder="Incidencias, observaciones…" value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} />
        <button className="btn" disabled={!text.trim()}>Enviar</button>
      </form>
    </section>
  )
}
