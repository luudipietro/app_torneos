import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { api } from '../api'
import StatsView from '../components/StatsView'
import { ErrorMsg, useAction, useLoad } from '../ui'

export default function Stats({ tid, admin }: { tid: number; admin: boolean }) {
  const { data, error } = useLoad(() => api.stats(tid), [tid])
  return (
    <div className="flex flex-col gap-4">
      {admin && <SharePanel tid={tid} />}
      <ErrorMsg msg={error} />
      {data && <StatsView stats={data} />}
    </div>
  )
}

function SharePanel({ tid }: { tid: number }) {
  const link = useLoad(() => api.publicLink(tid), [tid])
  const [qr, setQr] = useState('')
  const [copied, setCopied] = useState(false)
  const act = useAction()
  const token = link.data?.token
  const url = token ? `${location.origin}/p/${token}` : ''

  useEffect(() => {
    if (!url) { setQr(''); return }
    QRCode.toDataURL(url, { margin: 1, width: 280 }).then(setQr).catch(() => setQr(''))
  }, [url])

  const set = (enabled: boolean, regenerate = false) =>
    act.run(async () => { await api.setPublicLink(tid, enabled, regenerate); link.reload() })

  const copy = async () => {
    try { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000) }
    catch { window.prompt('Copiá el link:', url) }
  }

  return (
    <section className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">🔗 Vista pública</h2>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="h-5 w-5" checked={!!link.data?.enabled} disabled={act.busy || !link.data}
            onChange={(e) => { if (e.target.checked || confirm('El link actual dejará de funcionar. ¿Desactivar?')) void set(e.target.checked) }} />
          Activada
        </label>
      </div>
      <p className="text-sm text-slate-500">
        Cualquiera con el link puede ver posiciones, fixture, llaves y estadísticas, sin ingresar. No muestra DNI, fotos ni comentarios.
      </p>
      <ErrorMsg msg={act.error || link.error} />
      {url && (
        <>
          <div className="flex gap-2">
            <input className="input text-sm" readOnly value={url} onFocus={(e) => e.target.select()} />
            <button className="btn shrink-0" onClick={copy}>{copied ? '¡Copiado!' : 'Copiar'}</button>
          </div>
          {qr && (
            <div className="flex flex-col items-center gap-2">
              <img src={qr} alt="Código QR de la vista pública" className="h-48 w-48 rounded-lg border border-slate-200" />
              <a className="text-sm text-green-700 underline" href={qr} download="torneo-qr.png">Descargar QR para imprimir</a>
            </div>
          )}
          <div className="flex justify-between text-sm">
            <a className="text-green-700 underline" href={url} target="_blank" rel="noreferrer">Abrir vista pública</a>
            <button className="text-red-600" disabled={act.busy} onClick={() => { if (confirm('El link anterior dejará de funcionar y tendrás que compartir el nuevo. ¿Generar uno nuevo?')) void set(true, true) }}>
              Generar link nuevo
            </button>
          </div>
        </>
      )}
    </section>
  )
}
