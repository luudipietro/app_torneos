import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Bundle } from '../api'
import { applyOps } from './apply'
import {
  enqueue, fetchBundle, getMe, listConflicts, loadSnapshot, pendingOps, status, subscribe, type NewOp,
} from './queue'
import type { Conflict, Op } from './types'

/** Estado global de la sincronización, para el aviso de la parte superior. */
export function useSyncStatus() {
  const [state, setState] = useState({ ...status(), pending: 0, conflicts: [] as Conflict[] })
  useEffect(() => {
    let alive = true
    const read = async () => {
      const [pending, conflicts] = await Promise.all([pendingOps(), listConflicts()])
      if (alive) setState({ ...status(), pending: pending.length, conflicts })
    }
    void read()
    const off = subscribe(() => void read())
    return () => { alive = false; off() }
  }, [])
  return state
}

/**
 * Un partido listo para usar sin conexión: copia guardada del servidor + las acciones
 * pendientes aplicadas encima. Cada acción nueva se guarda en la cola local.
 */
export function useMatchBundle(matchId: number) {
  const [snap, setSnap] = useState<Bundle | null>(null)
  const [ops, setOps] = useState<Op[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      setSnap(await fetchBundle(matchId))
      setError('')
    } catch (e) {
      if (typeof (e as { status?: number }).status === 'number') setError((e as Error).message) // error real del servidor
      else if (!(await loadSnapshot(matchId))) setError('Sin conexión y sin datos guardados de este partido')
    }
    setOps(await pendingOps(matchId))
    setLoading(false)
  }, [matchId])

  useEffect(() => { void refresh() }, [refresh])

  // la cola cambió (acción nueva o sincronización): releer lo guardado en el dispositivo
  useEffect(() => subscribe(() => {
    void loadSnapshot(matchId).then((b) => b && setSnap(b))
    void pendingOps(matchId).then(setOps)
  }), [matchId])

  const me = getMe()
  const view = useMemo(() => (snap && me ? applyOps(snap, ops, me) : snap), [snap, ops]) // eslint-disable-line react-hooks/exhaustive-deps
  const dispatch = useCallback((n: Omit<NewOp, 'matchId'>) => enqueue({ ...n, matchId }), [matchId])
  return { view, loading, error, refresh, dispatch, pending: ops.length }
}
