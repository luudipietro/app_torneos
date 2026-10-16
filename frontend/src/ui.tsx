import { useCallback, useEffect, useState } from 'react'

/** Carga datos async y expone recarga + error. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const reload = useCallback(() => {
    fn().then((d) => { setData(d); setError('') }).catch((e) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(reload, [reload])
  return { data, error, reload }
}

export function ErrorMsg({ msg }: { msg: string }) {
  return msg ? <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{msg}</p> : null
}

/** Ejecuta una acción mostrando el error en pantalla. */
export function useAction() {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true); setError('')
    try { await fn(); return true } catch (e) { setError((e as Error).message); return false } finally { setBusy(false) }
  }
  return { error, busy, run }
}
