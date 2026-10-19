export type Tournament = { id: number; name: string; start_date: string | null; rules: Record<string, unknown>; my_role: 'admin' | 'scorer' }
export type Me = { id: number; email: string; name: string }
export type Member = { user_id: number; name: string; email: string; role: 'admin' | 'scorer' }
export type Invitation = { id: number; email: string; role: 'admin' | 'scorer' }
export type Members = { members: Member[]; invitations: Invitation[] }
export type Team = { id: number; tournament_id: number; name: string; crest_url: string | null; delegate: string | null; seed: number | null }
export type Player = { id: number; enabled: boolean; team_id: number; name: string; dni: string; birth_date: string | null; number: number | null; position: string | null }
export type DrawResult = { steps: { team_id: number; group: number }[]; groups: number[][] }
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
export type Cup = {
  name: string; positions: number[]; extra: { position: number; count: number }[]
  from_winners?: string[]; from_losers?: string[]; max_rounds?: number | null
  third_place?: boolean | null; avoid_same_group?: boolean | null
  pairing?: Pairing; pairing_seed?: number | null; manual_pairs?: [string, string][]
}
export type Pairing = 'seeded' | 'cross' | 'random' | 'manual'
export type Plan = { label: string; cups: Cup[] }
export type KnockoutConfig = KnockoutOptions & { auto_create: boolean; picked: number | null }
export type KnockoutOptions = { cups: Cup[]; third_place: boolean; avoid_same_group: boolean }
export type Entrant = { seed: number; team_id: number | null; group_id: number | null; group_name: string | null; position: number | null; points: number | null; gd: number | null; label: string | null; code: string; bye: boolean }
export type Pair = { home: Entrant; away: Entrant }
export type CupPreview = { name: string; size: number; byes: number; rounds: number; total_rounds: number; entrants: Entrant[]; pairs: Pair[] }
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
  cups: { name: string; rounds: number; total_rounds: number | null; matches: PublicMatch[] }[]
  stats: Stats; updated_at: string
}
export type PublicEvent = { minute: number | null; type: string; player_name: string; team_id: number }
export type PublicLink = { enabled: boolean; token: string | null }
export type Row = { team_id: number; played: number; won: number; drawn: number; lost: number; gf: number; ga: number; gd: number; points: number }
export type GroupStandings = { group_id: number; name: string; rows: Row[] }
