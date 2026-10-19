import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, LineupPlayer } from '../../api'
import { useMatchBundle } from '../../offline/hooks'
import { shrinkImage } from '../../offline/image'
import { newId } from '../../offline/queue'
import { ErrorMsg, useAction } from '../../ui'
import Assignees from './Assignees'
import CloseMatch from './CloseMatch'
import Comments from './Comments'
import { Pending, STATUS, TYPES } from './constants'
import EventForm from './EventForm'
import QuickResult from './QuickResult'
import Schedule from './Schedule'
import Sheets from './Sheets'

export default function MatchPage({ tid, admin }: { tid: number; admin: boolean }) {
  const mid = Number(useParams().mid)
  const { view, loading, error, refresh, dispatch, pending } = useMatchBundle(mid)
  const act = useAction()

  if (!view) return <ErrorMsg msg={error || (loading ? '' : 'No se pudo cargar el partido')} />
  const d = view.detail
  const lu = view.lineup
  const closed = d.status === 'finished'
  const sides = lu ? [lu.home, lu.away] : []
  const tname = (id: number | null) => sides.find((s) => s.team_id === id)?.team_name ?? 'A definir'
  const players = new Map<number, LineupPlayer>(sides.flatMap((s) => s.players.map((p) => [p.player_id, p] as const)))
  // si ya se tomó buena fe de un equipo, solo los presentes pueden recibir incidencias
  const eligible = (side: (typeof sides)[number]) => {
    const present = side.players.filter((p) => p.present)
    return present.length > 0 ? present : side.players.filter((p) => !p.suspension && p.enabled)
  }

  return (
    <div className="flex flex-col gap-4">
      <Link to={d.is_knockout ? `/t/${tid}/llaves` : `/t/${tid}/grupos`} className="text-sm text-slate-500">← {d.is_knockout ? 'Llaves' : 'Grupos y partidos'}</Link>
      <ErrorMsg msg={error} />

      <section className="card flex flex-col items-center gap-2">
        <span className={`rounded-full px-3 py-0.5 text-xs font-semibold ${closed ? 'bg-slate-200 text-slate-700' : 'bg-green-100 text-green-800'}`}>
          {STATUS[d.status] ?? d.status}
        </span>
        <div className="flex w-full items-center justify-between gap-2 text-center">
          <span className="flex-1 font-semibold">{tname(d.home_team_id)}</span>
          <span className="text-3xl font-bold tabular-nums">
            {d.home_goals ?? '–'} : {d.away_goals ?? '–'}
            {d.home_pens != null && <span className="block text-sm font-normal text-slate-500">pen. {d.home_pens} - {d.away_pens}</span>}
          </span>
          <span className="flex-1 font-semibold">{tname(d.away_team_id)}</span>
        </div>
        {(d.scheduled_at || d.venue) && (
          <p className="text-sm text-slate-500">
            📅 {[d.scheduled_at && new Date(d.scheduled_at).toLocaleString('es-AR', { weekday: 'long', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }), d.venue].filter(Boolean).join(' · ')}
          </p>
        )}
        {lu && (
          <Link to={`/t/${tid}/partido/${mid}/buena-fe`} className="btn-ghost w-full text-center">
            ✅ Control de buena fe ({lu.home.present_count} / {lu.away.present_count})
          </Link>
        )}
        <ErrorMsg msg={act.error} />
        {closed ? (
          admin && (
            <button className="btn-ghost" disabled={act.busy} onClick={() => act.run(async () => { await api.reopenMatch(mid); await refresh() })}>
              Reabrir (organizador)
            </button>
          )
        ) : (
          <CloseMatch d={d} home={tname(d.home_team_id)} away={tname(d.away_team_id)}
            onClose={(pens) => dispatch({ kind: 'match.finish', payload: pens ?? {} })} />
        )}
        {pending > 0 && (
          <p className="text-xs text-amber-700">
            ⏳ {pending} cambio{pending > 1 ? 's' : ''} guardado{pending > 1 ? 's' : ''} en este dispositivo, pendiente{pending > 1 ? 's' : ''} de sincronizar
          </p>
        )}
      </section>

      {admin && <Schedule matchId={mid} scheduledAt={d.scheduled_at} venue={d.venue} onSaved={refresh} />}

      {admin && <Assignees tid={tid} matchId={mid} current={d.assignee_ids} />}

      {!closed && lu && (
        <EventForm
          sides={[{ name: lu.home.team_name, players: eligible(lu.home) }, { name: lu.away.team_name, players: eligible(lu.away) }]}
          onAdd={(playerId, type, minute) => dispatch({ kind: 'event.add', payload: { player_id: playerId, type, minute, client_id: newId() } })}
        />
      )}
      {!closed && lu && d.events.length === 0 && (
        <QuickResult d={d} home={lu.home.team_name} away={lu.away.team_name} onSaved={refresh} />
      )}
      {!closed && !lu && <p className="card text-sm text-slate-500">Este partido todavía no tiene los dos equipos definidos.</p>}

      <section className="card flex flex-col gap-2">
        <h2 className="font-semibold">Incidencias</h2>
        {d.events.length === 0 && <p className="text-sm text-slate-400">Todavía no hay goles ni tarjetas.</p>}
        <ul className="flex flex-col gap-1.5 text-sm">
          {d.events.map((e) => (
            <li key={e.id} className="flex items-center gap-2">
              <span className="w-9 text-right tabular-nums text-slate-400">{e.minute != null ? `${e.minute}'` : ''}</span>
              <span title={TYPES[e.type]?.label}>{TYPES[e.type]?.icon}</span>
              <span className="flex-1">
                {players.get(e.player_id)?.name ?? '?'} <span className="text-slate-400">· {tname(e.team_id)}{e.type === 'own_goal' && ' (en contra)'}</span>
                {e.pending && <Pending />}
              </span>
              {!closed && (
                <button className="text-red-600" onClick={() => dispatch({ kind: 'event.delete', payload: e.client_id ? { client_id: e.client_id } : { id: e.id } })}>✕</button>
              )}
            </li>
          ))}
        </ul>
      </section>

      <Sheets
        d={d}
        closed={closed}
        onUpload={async (f) => dispatch({ kind: 'sheet.upload', blob: await shrinkImage(f) })}
        onDelete={(id) => act.run(async () => { await api.deleteSheet(id); await refresh() })}
      />

      <Comments
        d={d}
        onAdd={(text) => dispatch({ kind: 'comment.add', payload: { text } })}
        onDelete={(id) => act.run(async () => { await api.deleteComment(mid, id); await refresh() })}
      />
    </div>
  )
}
