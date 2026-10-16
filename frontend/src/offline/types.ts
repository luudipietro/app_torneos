export type OpKind = 'lineup.mark' | 'lineup.unmark' | 'event.add' | 'event.delete' | 'comment.add' | 'match.finish' | 'sheet.upload'

/** Acción cargada en la cancha que todavía no confirmó el servidor. */
export type Op = {
  seq?: number // clave autoincremental de la cola: define el orden de envío
  id: string // id único; el servidor lo usa para no aplicarla dos veces
  userId: number
  kind: OpKind
  matchId: number
  payload: Record<string, unknown>
  blob?: Blob // solo sheet.upload
  createdAt: string
}

/** Operación que el servidor no pudo aplicar (gana la versión del servidor). */
export type Conflict = {
  id?: number
  opId: string
  userId: number
  kind: OpKind
  matchId: number
  payload: Record<string, unknown>
  message: string
  at: string
}

export type Me = { id: number; name: string }
