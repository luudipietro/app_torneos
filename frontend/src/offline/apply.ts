import type { Bundle, LineupPlayer, LineupSide } from '../api'
import type { Me, Op } from './types'

const HOME_GOALS = ['goal', 'penalty_goal']

/** Mismo criterio que el servidor: el gol en contra suma al rival del jugador. */
function recomputeScore(b: Bundle) {
  const d = b.detail
  let home = 0
  let away = 0
  for (const e of d.events) {
    let scorer: number | null = null
    if (HOME_GOALS.includes(e.type)) scorer = e.team_id
    else if (e.type === 'own_goal') scorer = e.team_id === d.home_team_id ? d.away_team_id : d.home_team_id
    else continue
    if (scorer === d.home_team_id) home++
    else away++
  }
  d.home_goals = home
  d.away_goals = away
  if (d.status === 'scheduled') d.status = 'in_progress'
}

function findPlayer(b: Bundle, id: number): { p: LineupPlayer; side: LineupSide } | null {
  if (!b.lineup) return null
  for (const side of [b.lineup.home, b.lineup.away]) {
    const p = side.players.find((x) => x.player_id === id)
    if (p) return { p, side }
  }
  return null
}

const recount = (side: LineupSide) => { side.present_count = side.players.filter((x) => x.present).length }

function applyOne(b: Bundle, op: Op, me: Me) {
  const d = b.detail
  const p = op.payload
  const localId = -(op.seq ?? 1) // ids negativos = todavía no existen en el servidor
  switch (op.kind) {
    case 'lineup.mark':
    case 'lineup.unmark': {
      const f = findPlayer(b, Number(p.player_id))
      if (!f) return
      if (op.kind === 'lineup.mark') {
        if (f.p.suspension || !f.p.enabled) return // el servidor lo rechazaría
        f.p.present = true
        f.p.verified_by = me.name
        f.p.verified_at = op.createdAt
      } else {
        f.p.present = false
        f.p.verified_by = null
        f.p.verified_at = null
      }
      recount(f.side)
      return
    }
    case 'event.add': {
      const team = findPlayer(b, Number(p.player_id))?.side.team_id ?? Number(p.team_id)
      d.events.push({
        id: localId, client_id: String(p.client_id ?? ''), team_id: team, player_id: Number(p.player_id),
        type: String(p.type), minute: p.minute == null ? null : Number(p.minute), pending: true,
      })
      d.events.sort((x, y) => (x.minute ?? 999) - (y.minute ?? 999) || x.id - y.id)
      recomputeScore(b)
      return
    }
    case 'event.delete': {
      const before = d.events.length
      d.events = d.events.filter((e) => !((p.id != null && e.id === p.id) || (p.client_id && e.client_id === p.client_id)))
      if (d.events.length !== before) recomputeScore(b)
      return
    }
    case 'comment.add':
      d.comments.push({ id: localId, user_id: me.id, author: me.name, text: String(p.text), created_at: op.createdAt.replace('Z', ''), pending: true })
      return
    case 'match.finish':
      if (d.home_goals == null) d.home_goals = d.away_goals = 0
      d.status = 'finished'
      if (p.home_pens != null) { d.home_pens = Number(p.home_pens); d.away_pens = Number(p.away_pens) }
      return
    case 'sheet.upload':
      d.sheets.push({ id: localId, content_type: op.blob?.type ?? 'image/jpeg', pending: true, localBlob: op.blob })
  }
}

/**
 * Lo que se ve en pantalla: la última copia del servidor con las acciones pendientes
 * aplicadas encima, en el orden en que se cargaron. No modifica ``base``.
 */
export function applyOps(base: Bundle, ops: Op[], me: Me): Bundle {
  const b: Bundle = structuredClone(base)
  for (const op of ops) if (op.matchId === b.detail.id) applyOne(b, op, me)
  return b
}
