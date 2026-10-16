import type { Bundle } from '../api'
import { getToken } from '../api'
import { idb, STORES } from './idb'
import type { Conflict, Me, Op, OpKind } from './types'

type Listener = () => void
const listeners = new Set<Listener>()
const emit = () => listeners.forEach((fn) => fn())
export const subscribe = (fn: Listener) => { listeners.add(fn); return () => { listeners.delete(fn) } }

// ---------- usuario actual ----------
export const getMe = (): Me | null => {
  try { return JSON.parse(localStorage.getItem('me') ?? 'null') } catch { return null }
}
export const setMe = (me: Me | null) => (me ? localStorage.setItem('me', JSON.stringify(me)) : localStorage.removeItem('me'))

export const newId = () =>
  globalThis.crypto?.randomUUID?.() ?? Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('')

// ---------- estado de conexión ----------
let online = typeof navigator === 'undefined' || navigator.onLine !== false
let syncing = false
export const status = () => ({ online, syncing })
function setStatus(next: { online?: boolean; syncing?: boolean }) {
  const changed = (next.online ?? online) !== online || (next.syncing ?? syncing) !== syncing
  online = next.online ?? online
  syncing = next.syncing ?? syncing
  if (changed) emit()
}

// ---------- cola ----------
const allOps = () => idb.all<Op>(STORES.outbox)

export async function pendingOps(matchId?: number): Promise<Op[]> {
  const uid = getMe()?.id
  const ops = (await allOps()).filter((o) => o.userId === uid)
  return matchId == null ? ops : ops.filter((o) => o.matchId === matchId)
}

export type NewOp = { kind: OpKind; matchId: number; payload?: Record<string, unknown>; blob?: Blob }

/**
 * Anota una acción para enviarla al servidor. Se guarda en el dispositivo y, si hay
 * conexión, se sincroniza enseguida. Dos acciones que se anulan entre sí (marcar y
 * desmarcar, cargar y borrar un gol todavía sin enviar) se cancelan sin viajar.
 */
export async function enqueue(n: NewOp): Promise<void> {
  const me = getMe()
  if (!me) throw new Error('No hay sesión')
  const payload = n.payload ?? {}
  const mine = (await allOps()).filter((o) => o.userId === me.id && o.matchId === n.matchId)
  let cancel: Op | undefined
  if (n.kind === 'event.delete' && payload.client_id) {
    cancel = mine.find((o) => o.kind === 'event.add' && o.payload.client_id === payload.client_id)
  } else if (n.kind === 'lineup.unmark' || n.kind === 'lineup.mark') {
    const opposite = n.kind === 'lineup.mark' ? 'lineup.unmark' : 'lineup.mark'
    cancel = [...mine].reverse().find((o) => o.kind === opposite && o.payload.player_id === payload.player_id)
  }
  if (cancel) {
    await idb.del(STORES.outbox, cancel.seq!)
  } else {
    const op: Op = { id: newId(), userId: me.id, kind: n.kind, matchId: n.matchId, payload, blob: n.blob, createdAt: new Date().toISOString() }
    await idb.add(STORES.outbox, op)
  }
  emit()
  void flush()
}

export const listConflicts = (): Promise<Conflict[]> =>
  idb.all<Conflict>(STORES.conflicts).then((c) => c.filter((x) => x.userId === getMe()?.id))
export async function dismissConflict(id: number) { await idb.del(STORES.conflicts, id); emit() }
export async function dismissAllConflicts() {
  for (const c of await listConflicts()) await idb.del(STORES.conflicts, c.id!)
  emit()
}

// ---------- copias locales de los partidos ----------
export async function saveSnapshot(bundle: Bundle) {
  await idb.put(STORES.snapshots, { matchId: bundle.detail.id, bundle, savedAt: new Date().toISOString() })
}
export const loadSnapshot = async (matchId: number): Promise<Bundle | null> =>
  (await idb.get<{ bundle: Bundle }>(STORES.snapshots, matchId))?.bundle ?? null

// ---------- red ----------
class NetworkError extends Error {}
class AuthError extends Error {}

async function call(path: string, init: RequestInit): Promise<{ status: number; json: any }> {
  let res: Response
  try {
    res = await fetch('/api' + path, { ...init, headers: { ...(init.headers ?? {}), Authorization: `Bearer ${getToken()}` } })
  } catch {
    throw new NetworkError()
  }
  if (res.status === 401) throw new AuthError()
  let json: any = null
  try { json = await res.json() } catch { /* sin cuerpo */ }
  return { status: res.status, json }
}

/** Baja el partido del servidor y lo guarda en el dispositivo (para usarlo sin conexión). */
export async function fetchBundle(matchId: number): Promise<Bundle> {
  const { status, json } = await call(`/matches/${matchId}/bundle`, {})
  if (status >= 400) throw Object.assign(new Error(typeof json?.detail === 'string' ? json.detail : 'Error'), { status })
  await saveSnapshot(json)
  setStatus({ online: true })
  return json
}

const detailOf = (json: any) => (typeof json?.detail === 'string' ? json.detail : 'Error')

async function sendSheet(op: Op): Promise<{ done: boolean; conflict?: string }> {
  const f = new FormData()
  f.append('file', op.blob!, op.blob!.type.includes('png') ? 'planilla.png' : 'planilla.jpg')
  f.append('client_id', op.id)
  const { status, json } = await call(`/matches/${op.matchId}/sheets`, { method: 'POST', body: f })
  if (status < 300) return { done: true }
  if (status >= 500) throw new NetworkError() // reintentar más tarde
  return { done: true, conflict: detailOf(json) }
}

const BATCH = 20
let flushing: Promise<void> | null = null

/** Envía la cola en orden. Se corta ante falta de señal o error del servidor y reintenta después. */
export function flush(): Promise<void> {
  flushing ??= doFlush().finally(() => { flushing = null; setStatus({ syncing: false }) })
  return flushing
}

async function doFlush(): Promise<void> {
  const me = getMe()
  if (!me || !getToken()) return
  if (!(await allOps()).some((o) => o.userId === me.id)) return // nada que enviar: no molestar a la pantalla
  setStatus({ syncing: true })
  try {
    for (;;) {
      const ops = (await allOps()).filter((o) => o.userId === me.id)
      if (!ops.length) break
      const done: Op[] = []
      const conflicts: { op: Op; message: string }[] = []
      let stop = false

      if (ops[0].kind === 'sheet.upload') {
        const r = await sendSheet(ops[0])
        done.push(ops[0])
        if (r.conflict) conflicts.push({ op: ops[0], message: r.conflict })
      } else {
        const batch: Op[] = []
        for (const o of ops) { if (o.kind === 'sheet.upload' || batch.length >= BATCH) break; batch.push(o) }
        const { status, json } = await call('/sync', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ops: batch.map((o) => ({ id: o.id, type: o.kind, match_id: o.matchId, payload: o.payload })) }),
        })
        if (status >= 500) throw new NetworkError()
        if (status >= 400) throw new Error(detailOf(json)) // lote mal formado: no tiene arreglo reintentando
        const byId = new Map<string, Op>(batch.map((o) => [o.id, o]))
        for (const r of json.results as { id: string; status: string; message?: string }[]) {
          const op = byId.get(r.id)!
          if (r.status === 'error') { stop = true; break }
          done.push(op)
          if (r.status === 'rejected') conflicts.push({ op, message: r.message ?? 'No se pudo aplicar' })
        }
      }

      // el servidor ya confirmó: se actualiza la copia local ANTES de quitar de la cola,
      // así la pantalla no parpadea entre "pendiente" y "sincronizado"
      for (const id of new Set(done.map((o) => o.matchId))) {
        try { await fetchBundle(id) } catch { /* sin datos nuevos: se actualizará al abrir el partido */ }
      }
      for (const c of conflicts) {
        await idb.add(STORES.conflicts, {
          opId: c.op.id, userId: c.op.userId, kind: c.op.kind, matchId: c.op.matchId,
          payload: c.op.payload, message: c.message, at: new Date().toISOString(),
        } satisfies Conflict)
      }
      for (const o of done) await idb.del(STORES.outbox, o.seq!)
      setStatus({ online: true })
      emit()
      if (stop || !done.length) break
    }
  } catch (e) {
    if (e instanceof NetworkError) setStatus({ online: false })
    // AuthError u otros: la cola se conserva; se reintenta al volver a ingresar
  }
}

// ---------- arranque ----------
let started = false
export function startSync() {
  if (started || typeof window === 'undefined') return
  started = true
  window.addEventListener('online', () => { setStatus({ online: true }); void flush() })
  window.addEventListener('offline', () => setStatus({ online: false }))
  setInterval(() => { if (getToken()) void flush() }, 15000) // reintento periódico (señal inestable)
  void flush()
}
