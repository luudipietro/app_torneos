export type Tournament = { id: number; name: string; start_date: string | null; rules: Record<string, unknown>; my_role: 'admin' | 'scorer' }
export type Me = { id: number; email: string; name: string }
export type Member = { user_id: number; name: string; email: string; role: 'admin' | 'scorer' }
export type Invitation = { id: number; email: string; role: 'admin' | 'scorer' }
export type Members = { members: Member[]; invitations: Invitation[] }
export type Team = { id: number; tournament_id: number; name: string; crest_url: string | null; delegate: string | null; seed: number | null }
export type Player = { id: number; enabled: boolean; team_id: number; name: string; dni: string; birth_date: string | null; number: number | null; position: string | null }
export type Layout = { n_groups: number; sizes: number[]; balanced: boolean }
export type Group = { id: number; name: string; team_ids: number[] }
export type Stage = { id: number; order: number; type: string; name: string; config: Record<string, unknown>; groups: Group[] }
export type Match = { id: number; stage_id: number; group_id: number | null; round: number; home_team_id: number | null; away_team_id: number | null; home_goals: number | null; away_goals: number | null; status: string; assignee_ids: number[]; home_pens: number | null; away_pens: number | null; is_knockout: boolean; is_third_place: boolean; scheduled_at: string | null; venue: string | null }
export type MatchEvent = { id: number; client_id?: string | null; team_id: number; player_id: number; type: string; minute: number | null; pending?: boolean }
export type Sheet = { id: number; content_type: string; pending?: boolean; localBlob?: Blob }
export type Comment = { id: number; user_id: number; author: string; text: string; created_at: string; pending?: boolean }
export type MatchDetail = Match & { events: MatchEvent[]; sheets: Sheet[]; comments: Comment[] }
export type LineupPlayer = {
  player_id: number; name: string; dni: string; number: number | null; has_photo: boolean; enabled: boolean
  present: boolean; verified_by: string | null; verified_at: string | null
  suspension: { remaining: number; reason: 'yellows' | 'red' } | null; yellows: number
}
export type LineupSide = { team_id: number; team_name: string; players: LineupPlayer[]; present_count: number }
export type Lineup = { match_id: number; status: string; home: LineupSide; away: LineupSide }
export type TournamentSuspension = { team_id: number; team_name: string; player_id: number; player_name: string; remaining: number; reason: 'yellows' | 'red' }
export type Cup = { name: string; positions: number[]; extra: { position: number; count: number }[] }
export type Plan = { label: string; cups: Cup[] }
export type KnockoutOptions = { cups: Cup[]; third_place: boolean; avoid_same_group: boolean }
export type Entrant = { seed: number; team_id: number; group_id: number; group_name: string; position: number; points: number; gd: number }
export type CupPreview = { name: string; size: number; byes: number; rounds: number; entrants: Entrant[] }
export type KnockoutPreview = { unplayed: number; cups: CupPreview[] }
export type Bundle = { detail: MatchDetail; lineup: Lineup | null }
export type ScorerRow = { rank: number; player_id: number; name: string; team_id: number; team_name: string; goals: number; penalties: number }
export type CardRow = { player_id: number; name: string; team_id: number; team_name: string; yellow: number; red: number }
export type DefenseRow = { rank: number; team_id: number; team_name: string; played: number; goals_against: number; average: number; clean_sheets: number }
export type FairPlayRow = { team_id: number; team_name: string; yellow: number; red: number; points: number }
export type Stats = {
  matches_played: number; total_goals: number; goals_per_match: number
  scorers: ScorerRow[]; cards: CardRow[]; defense: DefenseRow[]; fair_play: FairPlayRow[]; suspensions: TournamentSuspension[]
}
export type PublicMatch = Pick<Match, 'id' | 'round' | 'group_id' | 'home_team_id' | 'away_team_id' | 'home_goals' | 'away_goals' | 'home_pens' | 'away_pens' | 'status' | 'scheduled_at' | 'venue' | 'is_third_place'>
export type PublicData = {
  name: string; start_date: string | null; teams: { id: number; name: string; crest_url: string | null }[]
  groups_name: string | null; groups: { id: number; name: string; standings: Row[]; matches: PublicMatch[] }[]
  cups: { name: string; rounds: number; matches: PublicMatch[] }[]
  stats: Stats; updated_at: string
}
export type PublicEvent = { minute: number | null; type: string; player_name: string; team_id: number }
export type PublicLink = { enabled: boolean; token: string | null }
export type Row = { team_id: number; played: number; won: number; drawn: number; lost: number; gf: number; ga: number; gd: number; points: number }
export type GroupStandings = { group_id: number; name: string; rows: Row[] }

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
  deleteTeam: (id: number) => req<void>('DELETE', `/teams/${id}`),
  players: (teamId: number) => req<Player[]>('GET', `/teams/${teamId}/players`),
  createPlayer: (teamId: number, data: { name: string; dni: string; number?: number | null; position?: string | null }) => req<Player>('POST', `/teams/${teamId}/players`, data),
  deletePlayer: (id: number) => req<void>('DELETE', `/players/${id}`),
  layouts: (tid: number) => req<Layout[]>('GET', `/tournaments/${tid}/layouts`),
  stages: (tid: number) => req<Stage[]>('GET', `/tournaments/${tid}/stages`),
  createGroups: (tid: number, data: { n_groups: number; double_round: boolean; seed?: number | null }) => req<Stage>('POST', `/tournaments/${tid}/stages/groups`, data),
  deleteStage: (id: number) => req<void>('DELETE', `/stages/${id}`),
  matches: (stageId: number) => req<Match[]>('GET', `/stages/${stageId}/matches`),
  setResult: (matchId: number, home_goals: number, away_goals: number) => req<Match>('PUT', `/matches/${matchId}/result`, { home_goals, away_goals }),
  standings: (stageId: number) => req<GroupStandings[]>('GET', `/stages/${stageId}/standings`),
  match: (id: number) => req<MatchDetail>('GET', `/matches/${id}`),
  addEvent: (id: number, data: { player_id: number; type: string; minute: number | null }) => req<MatchDetail>('POST', `/matches/${id}/events`, data),
  deleteEvent: (id: number, eventId: number) => req<MatchDetail>('DELETE', `/matches/${id}/events/${eventId}`),
  finishMatch: (id: number, pens?: { home_pens: number; away_pens: number }) => req<Match>('POST', `/matches/${id}/finish`, pens ?? {}),
  knockoutPlans: (tid: number) => req<Plan[]>('GET', `/tournaments/${tid}/knockout/plans`),
  knockoutPreview: (tid: number, o: KnockoutOptions) => req<KnockoutPreview>('POST', `/tournaments/${tid}/knockout/preview`, o),
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
