import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Bundle, LineupPlayer } from '../api'
import { applyOps } from './apply'
import { resetDb } from './idb'
import { dismissAllConflicts, enqueue, flush, listConflicts, loadSnapshot, pendingOps, setMe, status } from './queue'
import type { Op } from './types'

const ME = { id: 7, name: 'Pepe' }

function player(id: number, extra: Partial<LineupPlayer> = {}): LineupPlayer {
  return {
    player_id: id, name: `J${id}`, dni: `${id}0000000`, number: id, has_photo: false, enabled: true, present: false,
    verified_by: null, verified_at: null, suspension: null, yellows: 0, ...extra,
  }
}

function bundle(): Bundle {
  return {
    detail: {
      id: 10, stage_id: 1, group_id: 1, round: 1, home_team_id: 1, away_team_id: 2, home_goals: null, away_goals: null,
      status: 'scheduled', assignee_ids: [7], home_pens: null, away_pens: null, is_knockout: false, is_third_place: false, scheduled_at: null, venue: null,
      events: [], sheets: [], comments: [],
    },
    lineup: {
      match_id: 10, status: 'scheduled',
      home: { team_id: 1, team_name: 'Local', present_count: 0, players: [player(11), player(12, { suspension: { remaining: 1, reason: 'red' } })] },
      away: { team_id: 2, team_name: 'Visita', present_count: 0, players: [player(21), player(22)] },
    },
  }
}

let seq = 0
const op = (kind: Op['kind'], payload: Op['payload'] = {}, matchId = 10): Op => ({
  seq: ++seq, id: `op-${seq}-aaaaaaaa`, userId: ME.id, kind, matchId, payload, createdAt: '2026-10-15T20:00:00.000Z',
})

describe('applyOps', () => {
  it('no modifica la copia del servidor', () => {
    const base = bundle()
    const snapshot = JSON.stringify(base)
    applyOps(base, [op('lineup.mark', { player_id: 11 }), op('event.add', { player_id: 11, type: 'goal', client_id: 'c1' })], ME)
    expect(JSON.stringify(base)).toBe(snapshot)
  })

  it('marca y desmarca presentes y cuenta por equipo', () => {
    const v = applyOps(bundle(), [op('lineup.mark', { player_id: 11 }), op('lineup.mark', { player_id: 21 }), op('lineup.unmark', { player_id: 21 })], ME)
    expect(v.lineup!.home.players[0]).toMatchObject({ present: true, verified_by: 'Pepe' })
    expect([v.lineup!.home.present_count, v.lineup!.away.present_count]).toEqual([1, 0])
  })

  it('no deja marcar a un suspendido (el servidor lo rechazaría)', () => {
    const v = applyOps(bundle(), [op('lineup.mark', { player_id: 12 })], ME)
    expect(v.lineup!.home.players[1].present).toBe(false)
  })

  it('goles actualizan el marcador y el estado; tarjetas no', () => {
    const v = applyOps(bundle(), [
      op('event.add', { player_id: 11, type: 'goal', minute: 10, client_id: 'a' }),
      op('event.add', { player_id: 21, type: 'penalty_goal', minute: 20, client_id: 'b' }),
      op('event.add', { player_id: 22, type: 'yellow', minute: 30, client_id: 'c' }),
      op('event.add', { player_id: 21, type: 'own_goal', minute: 40, client_id: 'd' }), // en contra del visitante: suma al local
    ], ME)
    expect([v.detail.home_goals, v.detail.away_goals, v.detail.status]).toEqual([2, 1, 'in_progress'])
    expect(v.detail.events.map((e) => e.minute)).toEqual([10, 20, 30, 40])
    expect(v.detail.events.every((e) => e.pending && e.id < 0)).toBe(true)
    expect(v.detail.events.find((e) => e.client_id === 'b')!.team_id).toBe(2)
  })

  it('borra un evento por client_id o por id del servidor', () => {
    const base = bundle()
    base.detail.events = [{ id: 5, team_id: 1, player_id: 11, type: 'goal', minute: 3 }]
    base.detail.home_goals = 1
    const v = applyOps(base, [
      op('event.add', { player_id: 11, type: 'goal', client_id: 'x' }),
      op('event.delete', { client_id: 'x' }),
      op('event.delete', { id: 5 }),
    ], ME)
    expect(v.detail.events).toEqual([])
    expect(v.detail.home_goals).toBe(0)
  })

  it('comentarios, planilla y cierre con penales', () => {
    const blob = new Blob(['x'], { type: 'image/jpeg' })
    const v = applyOps(bundle(), [
      op('comment.add', { text: 'Llovizna' }),
      { ...op('sheet.upload'), blob },
      op('match.finish', { home_pens: 4, away_pens: 3 }),
    ], ME)
    expect(v.detail.comments[0]).toMatchObject({ text: 'Llovizna', author: 'Pepe', pending: true })
    expect(v.detail.sheets[0]).toMatchObject({ pending: true, localBlob: blob })
    expect(v.detail).toMatchObject({ status: 'finished', home_goals: 0, away_goals: 0, home_pens: 4, away_pens: 3 })
  })

  it('ignora operaciones de otros partidos', () => {
    const v = applyOps(bundle(), [op('comment.add', { text: 'otro' }, 99)], ME)
    expect(v.detail.comments).toEqual([])
  })
})

// ---------- cola ----------
type Handler = (url: string, init: RequestInit) => { status: number; json?: unknown } | 'network'
let calls: { url: string; body?: any; form?: FormData }[]

function mockServer(handler?: Partial<Record<string, Handler>>) {
  calls = []
  vi.stubGlobal('fetch', async (url: string, init: RequestInit = {}) => {
    const path = url.replace('/api', '')
    const isForm = init.body instanceof FormData
    calls.push({ url: path, body: !isForm && init.body ? JSON.parse(init.body as string) : undefined, form: isForm ? (init.body as FormData) : undefined })
    const key = path.startsWith('/sync') ? 'sync' : path.includes('/sheets') ? 'sheet' : 'bundle'
    const r = handler?.[key]?.(path, init) ?? defaults[key](path, init)
    if (r === 'network') throw new TypeError('Failed to fetch')
    return { status: r.status, json: async () => r.json } as Response
  })
}

const defaults: Record<string, Handler> = {
  sync: (_u, init) => ({ status: 200, json: { results: JSON.parse(init.body as string).ops.map((o: any) => ({ id: o.id, status: 'ok', code: 200 })) } }),
  sheet: () => ({ status: 201, json: {} }),
  bundle: () => ({ status: 200, json: bundle() }),
}

beforeEach(async () => {
  await resetDb()
  await new Promise((r) => { const q = indexedDB.deleteDatabase('torneos-offline'); q.onsuccess = q.onerror = q.onblocked = () => r(null) })
  localStorage.clear()
  localStorage.setItem('token', 'tok')
  setMe(ME)
  mockServer()
})

const sentOps = () => calls.filter((c) => c.url === '/sync').flatMap((c) => c.body.ops as { id: string; type: string; match_id: number }[])

describe('cola de operaciones', () => {
  it('envía en orden, guarda la copia del servidor y vacía la cola', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('sin señal') })) // primero sin conexión
    await enqueue({ kind: 'lineup.mark', matchId: 10, payload: { player_id: 11 } })
    await enqueue({ kind: 'event.add', matchId: 10, payload: { player_id: 11, type: 'goal', client_id: 'g1' } })
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: 'hola' } })
    await flush()
    expect((await pendingOps()).length).toBe(3)
    expect(status().online).toBe(false)

    mockServer() // vuelve la señal
    await flush()
    expect(await pendingOps()).toEqual([])
    expect(sentOps().map((o) => o.type)).toEqual(['lineup.mark', 'event.add', 'comment.add'])
    expect((await loadSnapshot(10))?.detail.id).toBe(10)
    expect(status().online).toBe(true)
  })

  it('un rechazo queda como conflicto y no frena el resto', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('x') }))
    await enqueue({ kind: 'lineup.mark', matchId: 10, payload: { player_id: 11 } })
    await enqueue({ kind: 'event.add', matchId: 10, payload: { player_id: 11, type: 'goal', client_id: 'g1' } })
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: 'ok' } })
    mockServer({
      sync: (_u, init) => {
        const ops = JSON.parse(init.body as string).ops
        return { status: 200, json: { results: ops.map((o: any, i: number) => (i === 1
          ? { id: o.id, status: 'rejected', code: 403, message: 'El partido está cerrado' }
          : { id: o.id, status: 'ok', code: 200 })) } }
      },
    })
    await flush()
    expect(await pendingOps()).toEqual([])
    const conflicts = await listConflicts()
    expect(conflicts).toHaveLength(1)
    expect(conflicts[0]).toMatchObject({ kind: 'event.add', message: 'El partido está cerrado', matchId: 10 })
    await dismissAllConflicts()
    expect(await listConflicts()).toEqual([])
  })

  it('error del servidor (5xx) conserva todo para reintentar', async () => {
    mockServer({ sync: () => ({ status: 503, json: {} }) })
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: 'a' } })
    await flush()
    expect((await pendingOps()).length).toBe(1)
    mockServer()
    await flush()
    expect(await pendingOps()).toEqual([])
  })

  it('si el servidor corta el lote con error, lo no procesado sigue en la cola', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('x') }))
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: '1' } })
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: '2' } })
    mockServer({
      sync: (_u, init) => {
        const ops = JSON.parse(init.body as string).ops
        return { status: 200, json: { results: [{ id: ops[0].id, status: 'ok', code: 200 }, { id: ops[1].id, status: 'error', code: 500 }] } }
      },
    })
    await flush()
    const left = await pendingOps()
    expect(left.map((o) => o.payload.text)).toEqual(['2'])
  })

  it('cancela pares que se anulan sin enviarlos', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('x') }))
    await enqueue({ kind: 'lineup.mark', matchId: 10, payload: { player_id: 11 } })
    await enqueue({ kind: 'lineup.unmark', matchId: 10, payload: { player_id: 11 } })
    await enqueue({ kind: 'event.add', matchId: 10, payload: { player_id: 11, type: 'goal', client_id: 'k' } })
    await enqueue({ kind: 'event.delete', matchId: 10, payload: { client_id: 'k' } })
    expect(await pendingOps()).toEqual([])
    // borrar algo que ya está en el servidor sí se envía
    await enqueue({ kind: 'event.delete', matchId: 10, payload: { id: 5 } })
    expect((await pendingOps()).map((o) => o.kind)).toEqual(['event.delete'])
  })

  it('las fotos viajan aparte, en su lugar de la cola, con su id para no duplicarse', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('x') }))
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: 'antes' } })
    await enqueue({ kind: 'sheet.upload', matchId: 10, blob: new Blob(['img'], { type: 'image/jpeg' }) })
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: 'despues' } })
    mockServer()
    await flush()
    const order = calls.filter((c) => c.url !== '/matches/10/bundle').map((c) => (c.form ? 'foto' : c.body.ops.map((o: any) => o.payload.text).join()))
    expect(order).toEqual(['antes', 'foto', 'despues'])
    const photo = calls.find((c) => c.form)!
    expect(photo.url).toBe('/matches/10/sheets')
    expect(String(photo.form!.get('client_id'))).toMatch(/^op-|^[0-9a-f-]{8,}/)
    expect(await pendingOps()).toEqual([])
  })

  it('solo envía lo del usuario actual', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('x') }))
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: 'mío' } })
    setMe({ id: 8, name: 'Otro' })
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: 'del otro' } })
    mockServer()
    await flush() // sincroniza el usuario 8
    expect(calls.find((c) => c.url === '/sync')!.body.ops).toHaveLength(1)
    expect((await pendingOps()).length).toBe(0)
    setMe(ME)
    expect((await pendingOps()).map((o) => o.payload.text)).toEqual(['mío']) // lo de ME sigue esperando su sesión
  })

  it('sin sesión (401) no pierde la cola', async () => {
    mockServer({ sync: () => ({ status: 401, json: {} }) })
    await enqueue({ kind: 'comment.add', matchId: 10, payload: { text: 'x' } })
    await flush()
    expect((await pendingOps()).length).toBe(1)
  })
})
