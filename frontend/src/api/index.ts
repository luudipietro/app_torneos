import type {
  Bundle, Comment, DrawResult, GroupStandings, Invitation, KnockoutConfig, KnockoutOptions, KnockoutPreview, Layout, Lineup, Match,
  MatchDetail, Me, Members, Plan, Player, PublicData, PublicEvent, PublicLink, PublicMatch, Stage, Stats, Team,
  Tournament, TournamentSuspension,
} from './types'

export * from './types'

const KEY = 'token'
export const getToken = () => localStorage.getItem(KEY)
export const setToken = (t: string | null) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY))

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

async function req<T>(method: string, path: string, body?: unknown | FormData): Promise<T> {
  const token = getToken()
  const isForm = body instanceof FormData
  const res = await fetch('/api' + path, {
    method,
    headers: { ...(body !== undefined && !isForm && { 'Content-Type': 'application/json' }), ...(token && { Authorization: `Bearer ${token}` }) },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  })
  if (res.status === 401 && token) { setToken(null); location.href = '/login' }
  if (!res.ok) {
    let msg = res.statusText
    try {
      const d = (await res.json()).detail
      msg = typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => x.msg).join('. ') : msg
    } catch { /* sin cuerpo */ }
    throw new ApiError(res.status, msg)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  login: (email: string, password: string) => req<{ access_token: string }>('POST', '/auth/login', { email, password }),
  register: (email: string, name: string, password: string) => req<{ access_token: string }>('POST', '/auth/register', { email, name, password }),
  stats: (tid: number) => req<Stats>('GET', `/tournaments/${tid}/stats`),
  publicLink: (tid: number) => req<PublicLink>('GET', `/tournaments/${tid}/public`),
  setPublicLink: (tid: number, enabled: boolean, regenerate = false) => req<PublicLink>('PUT', `/tournaments/${tid}/public`, { enabled, regenerate }),
  setSchedule: (matchId: number, scheduled_at: string | null, venue: string | null) => req<Match>('PUT', `/matches/${matchId}/schedule`, { scheduled_at, venue }),
  bundle: (id: number) => req<Bundle>('GET', `/matches/${id}/bundle`),
  me: () => req<Me>('GET', '/auth/me'),
  members: (tid: number) => req<Members>('GET', `/tournaments/${tid}/members`),
  invite: (tid: number, email: string, role: string) => req<Members>('POST', `/tournaments/${tid}/members`, { email, role }),
  removeMember: (tid: number, userId: number) => req<Members>('DELETE', `/tournaments/${tid}/members/${userId}`),
  cancelInvitation: (tid: number, id: number) => req<Members>('DELETE', `/tournaments/${tid}/invitations/${id}`),
  setAssignments: (matchId: number, user_ids: number[]) => req<Match>('PUT', `/matches/${matchId}/assignments`, { user_ids }),
  bulkAssign: (tid: number, user_id: number, match_ids: number[]) => req<Match[]>('POST', `/tournaments/${tid}/assignments`, { user_id, match_ids }),
  myMatches: (tid: number) => req<Match[]>('GET', `/tournaments/${tid}/my-matches`),
  tournaments: () => req<Tournament[]>('GET', '/tournaments'),
  tournament: (id: number) => req<Tournament>('GET', `/tournaments/${id}`),
  createTournament: (name: string, start_date: string | null) => req<Tournament>('POST', '/tournaments', { name, start_date }),
  teams: (tid: number) => req<Team[]>('GET', `/tournaments/${tid}/teams`),
  createTeam: (tid: number, data: { name: string; delegate?: string | null; seed?: number | null }) => req<Team>('POST', `/tournaments/${tid}/teams`, data),
  updateTeam: (id: number, data: { seed?: number | null; name?: string }) => req<Team>('PATCH', `/teams/${id}`, data),
  deleteTeam: (id: number) => req<void>('DELETE', `/teams/${id}`),
  players: (teamId: number) => req<Player[]>('GET', `/teams/${teamId}/players`),
  createPlayer: (teamId: number, data: { name: string; dni: string; number?: number | null; position?: string | null }) => req<Player>('POST', `/teams/${teamId}/players`, data),
  deletePlayer: (id: number) => req<void>('DELETE', `/players/${id}`),
  layouts: (tid: number) => req<Layout[]>('GET', `/tournaments/${tid}/layouts`),
  stages: (tid: number) => req<Stage[]>('GET', `/tournaments/${tid}/stages`),
  createGroups: (tid: number, data: { n_groups?: number; groups?: number[][]; double_round: boolean; seed?: number | null }) => req<Stage>('POST', `/tournaments/${tid}/stages/groups`, data),
  drawGroups: (tid: number, data: { n_groups: number; seed?: number | null; fixed?: Record<number, number> }) => req<DrawResult>('POST', `/tournaments/${tid}/stages/groups/draw`, data),
  deleteStage: (id: number) => req<void>('DELETE', `/stages/${id}`),
  matches: (stageId: number) => req<Match[]>('GET', `/stages/${stageId}/matches`),
  setResult: (matchId: number, home_goals: number, away_goals: number, pens?: { home_pens: number; away_pens: number }) => req<Match>('PUT', `/matches/${matchId}/result`, { home_goals, away_goals, ...pens }),
  standings: (stageId: number) => req<GroupStandings[]>('GET', `/stages/${stageId}/standings`),
  match: (id: number) => req<MatchDetail>('GET', `/matches/${id}`),
  addEvent: (id: number, data: { player_id: number; type: string; minute: number | null }) => req<MatchDetail>('POST', `/matches/${id}/events`, data),
  deleteEvent: (id: number, eventId: number) => req<MatchDetail>('DELETE', `/matches/${id}/events/${eventId}`),
  finishMatch: (id: number, pens?: { home_pens: number; away_pens: number }) => req<Match>('POST', `/matches/${id}/finish`, pens ?? {}),
  knockoutPlans: (tid: number) => req<Plan[]>('GET', `/tournaments/${tid}/knockout/plans`),
  knockoutPreview: (tid: number, o: KnockoutOptions) => req<KnockoutPreview>('POST', `/tournaments/${tid}/knockout/preview`, o),
  knockoutConfig: (tid: number) => req<KnockoutConfig | null>('GET', `/tournaments/${tid}/knockout/config`),
  saveKnockoutConfig: (tid: number, c: KnockoutConfig) => req<KnockoutConfig>('PUT', `/tournaments/${tid}/knockout/config`, c),
  createKnockout: (tid: number, o: KnockoutOptions) => req<Stage[]>('POST', `/tournaments/${tid}/stages/knockout`, o),
  reopenMatch: (id: number) => req<Match>('POST', `/matches/${id}/reopen`),
  uploadSheet: (id: number, file: File) => { const f = new FormData(); f.append('file', file); return req<MatchDetail>('POST', `/matches/${id}/sheets`, f) },
  deleteSheet: (id: number) => req<MatchDetail>('DELETE', `/sheets/${id}`),
  addComment: (id: number, text: string) => req<MatchDetail>('POST', `/matches/${id}/comments`, { text }),
  deleteComment: (id: number, commentId: number) => req<MatchDetail>('DELETE', `/matches/${id}/comments/${commentId}`),
  lineup: (id: number) => req<Lineup>('GET', `/matches/${id}/lineup`),
  markPresent: (id: number, playerId: number) => req<Lineup>('PUT', `/matches/${id}/lineup/${playerId}`),
  unmarkPresent: (id: number, playerId: number) => req<Lineup>('DELETE', `/matches/${id}/lineup/${playerId}`),
  onsitePlayer: (id: number, data: { team_id: number; name: string; dni: string; number?: number | null }) => req<Lineup>('POST', `/matches/${id}/lineup/new-player`, data),
  suspensions: (tid: number) => req<TournamentSuspension[]>('GET', `/tournaments/${tid}/suspensions`),
  setPlayerEnabled: (id: number, enabled: boolean) => req<Player>('PATCH', `/players/${id}`, { enabled }),
  uploadPlayerPhoto: (id: number, file: File) => { const f = new FormData(); f.append('file', file); return req<Player>('POST', `/players/${id}/photo`, f) },
}

/** Las imágenes requieren Authorization, así que se bajan como blob. */
export async function blobUrl(path: string): Promise<string> {
  const res = await fetch('/api' + path, { headers: { Authorization: `Bearer ${getToken()}` } })
  if (!res.ok) throw new ApiError(res.status, 'No se pudo cargar la imagen')
  return URL.createObjectURL(await res.blob())
}
export const sheetUrl = (id: number) => blobUrl(`/sheets/${id}/file`)
export const playerPhotoUrl = (id: number) => blobUrl(`/players/${id}/photo`)

/** Vista pública: sin sesión ni encabezado de autorización. */
async function pub<T>(path: string): Promise<T> {
  const res = await fetch('/api/public' + path)
  if (!res.ok) throw new ApiError(res.status, res.status === 404 ? 'Este link no existe o fue desactivado' : 'No se pudo cargar')
  return res.json()
}
export const publicApi = {
  tournament: (token: string) => pub<PublicData>(`/${token}`),
  match: (token: string, id: number) => pub<{ match: PublicMatch; events: PublicEvent[] }>(`/${token}/matches/${id}`),
}
