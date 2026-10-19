import { useEffect, useState } from 'react'
import { MatchDetail, sheetUrl } from '../../api'

function SheetImg({ id, blob }: { id: number; blob?: Blob }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    let u = ''
    if (blob) { u = URL.createObjectURL(blob); setUrl(u) }
    else sheetUrl(id).then((x) => { u = x; setUrl(x) }).catch(() => setUrl(''))
    return () => { if (u) URL.revokeObjectURL(u) }
  }, [id, blob])
  if (!url) return <div className="h-40 w-full animate-pulse rounded-lg bg-slate-100" />
  return <a href={url} target="_blank" rel="noreferrer"><img src={url} alt="Planilla del partido" className="max-h-80 w-full rounded-lg border border-slate-200 object-contain" /></a>
}

export default function Sheets({ d, closed, onUpload, onDelete }: { d: MatchDetail; closed: boolean; onUpload: (f: File) => Promise<void>; onDelete: (id: number) => Promise<unknown> }) {
  return (
    <section className="card flex flex-col gap-3">
      <h2 className="font-semibold">Foto de la planilla</h2>
      {d.sheets.map((s) => (
        <div key={s.id} className="flex flex-col gap-1">
          <SheetImg id={s.id} blob={s.localBlob} />
          {s.pending && <span className="text-xs text-amber-700">⏳ Se subirá cuando haya conexión</span>}
          {!closed && !s.pending && <button className="self-end text-sm text-red-600" onClick={() => onDelete(s.id)}>Quitar foto</button>}
        </div>
      ))}
      {!closed && (
        <label className="btn-ghost cursor-pointer text-center">
          📷 {d.sheets.length ? 'Agregar otra foto' : 'Sacar o subir foto'}
          <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden"
            onChange={async (e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) await onUpload(f) }} />
        </label>
      )}
      {closed && d.sheets.length === 0 && <p className="text-sm text-slate-400">Sin foto de planilla.</p>}
    </section>
  )
}
