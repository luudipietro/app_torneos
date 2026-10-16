import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, LineupPlayer, MatchDetail, sheetUrl } from '../api'
import { useMatchBundle } from '../offline/hooks'
import { shrinkImage } from '../offline/image'
import { newId } from '../offline/queue'
import { ErrorMsg, useAction, useLoad } from '../ui'

const TYPES: Record<string, { icon: string; label: string }> = {
  goal: { icon: '⚽', label: 'Gol' },
  penalty_goal: { icon: '⚽', label: 'Gol de penal' },
  own_goal: { icon: '🥅', label: 'Gol en contra' },
  yellow: { icon: '🟨', label: 'Amarilla' },
  second_yellow: { icon: '🟨🟥', label: 'Doble amarilla' },
  red: { icon: '🟥', label: 'Roja' },
}

const STATUS: Record<string, string> = {
  scheduled: 'Programado',
  in_progress: 'En juego',
  finished: 'Finalizado',
}

const Pending = () => <span title="Pendiente de sincronizar" className="ml-1 text-amber-600">⏳</span>

export default function MatchPage({ tid, admin }: { tid: number; admin: boolean }) {
  const mid = Number(useParams().mid)
  const { view, loading, error, refresh, dispatch, pending } = useMatchBundle(mid)
  const act = useAction()
  const [pens, setPens] = useState({ h: '', a: '' })

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
  const tied = d.is_knockout && d.home_goals != null && d.home_goals === d.away_goals

  return (
    <div className="flex flex-col gap-4">
      <Link to={`/t/${tid}/grupos`} className="text-sm text-slate-500">← Grupos y partidos</Link>
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
          <>
            {tied && (
              <div className="flex w-full flex-col items-center gap-2 rounded-lg bg-amber-50 p-3">
                <span className="text-sm font-medium text-amber-800">Empate: se define por penales</span>
                <div className="flex items-center gap-2">
                  <input className="w-14 rounded-lg border border-slate-300 py-2 text-center" inputMode="numeric" placeholder="Local" value={pens.h} onChange={(e) => setPens({ ...pens, h: e.target.value.replace(/\D/g, '') })} />
                  <span>-</span>
                  <input className="w-14 rounded-lg border border-slate-300 py-2 text-center" inputMode="numeric" placeholder="Visita" value={pens.a} onChange={(e) => setPens({ ...pens, a: e.target.value.replace(/\D/g, '') })} />
                </div>
              </div>
            )}
            <button className="btn" disabled={tied && (pens.h === '' || pens.a === '' || pens.h === pens.a)}
              onClick={() => dispatch({ kind: 'match.finish', payload: tied ? { home_pens: Number(pens.h), away_pens: Number(pens.a) } : {} })}>
              Cerrar partido
            </button>
          </>
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

type Side = { name: string; players: LineupPlayer[] }

function EventForm({ sides, onAdd }: { sides: Side[]; onAdd: (p: number, t: string, min: number | null) => Promise<void> }) {
  const [idx, setIdx] = useState(0)
  const [player, setPlayer] = useState('')
  const [type, setType] = useState('goal')
  const [minute, setMinute] = useState('')
  const side = sides[idx]
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onAdd(Number(player), type, minute ? Number(minute) : null)
    setPlayer('')
    setMinute('')
  }
  return (
    <form onSubmit={submit} className="card flex flex-col gap-3">
      <h2 className="font-semibold">Cargar incidencia</h2>
      <div className="grid grid-cols-2 gap-2">
        {sides.map((s, i) => (
          <button type="button" key={s.name} onClick={() => { setIdx(i); setPlayer('') }}
            className={`rounded-lg border py-2.5 text-sm font-medium ${idx === i ? 'border-green-600 bg-green-50 text-green-800' : 'border-slate-300 bg-white'}`}>
            {s.name}
          </button>
        ))}
      </div>
      <select className="input" value={player} onChange={(e) => setPlayer(e.target.value)} required>
        <option value="">Jugador…</option>
        {side.players.map((p) => <option key={p.player_id} value={p.player_id}>{p.number != null ? `#${p.number} ` : ''}{p.name}</option>)}
      </select>
      {side.players.length === 0 && <p className="text-sm text-amber-700">Este equipo no tiene jugadores habilitados.</p>}
      <div className="grid grid-cols-3 gap-2">
        <select className="input col-span-2" value={type} onChange={(e) => setType(e.target.value)}>
          {Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v.icon} {v.label}</option>)}
        </select>
        <input className="input" inputMode="numeric" placeholder="Min." value={minute} onChange={(e) => setMinute(e.target.value.replace(/\D/g, ''))} />
      </div>
      <button className="btn" disabled={!player}>Agregar</button>
    </form>
  )
}

function SheetImg({ id, blob }: { id: number; blob?: Blob }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    let u = ''
    if (blob) { u = URL.createObjectURL(blob); setUrl(u) }
    else sheetUrl(id).then((x) => { u = x; setUrl(x) }).catch(() => setUrl(''))
    return () => { if (u) URL.revokeObjectURL(u) }
  }, [id, blob])
  if (!url) return <div className="h-40 w-full animate-pulse rounded-lg bg-slate-100" />
  return <a href={url} target="_blank" rel="noreferrer"><img src={url} alt="Planilla del partido" className="max-h-80 w-full rounded-lg border border-slate-200 object-contain" /></a>
}

function Sheets({ d, closed, onUpload, onDelete }: { d: MatchDetail; closed: boolean; onUpload: (f: File) => Promise<void>; onDelete: (id: number) => Promise<unknown> }) {
  return (
    <section className="card flex flex-col gap-3">
      <h2 className="font-semibold">Foto de la planilla</h2>
      {d.sheets.map((s) => (
        <div key={s.id} className="flex flex-col gap-1">
          <SheetImg id={s.id} blob={s.localBlob} />
          {s.pending && <span className="text-xs text-amber-700">⏳ Se subirá cuando haya conexión</span>}
          {!closed && !s.pending && <button className="self-end text-sm text-red-600" onClick={() => onDelete(s.id)}>Quitar foto</button>}
        </div>
      ))}
      {!closed && (
        <label className="btn-ghost cursor-pointer text-center">
          📷 {d.sheets.length ? 'Agregar otra foto' : 'Sacar o subir foto'}
          <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="hidden"
            onChange={async (e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) await onUpload(f) }} />
        </label>
      )}
      {closed && d.sheets.length === 0 && <p className="text-sm text-slate-400">Sin foto de planilla.</p>}
    </section>
  )
}

function Comments({ d, onAdd, onDelete }: { d: MatchDetail; onAdd: (t: string) => Promise<void>; onDelete: (id: number) => Promise<unknown> }) {
  const [text, setText] = useState('')
  return (
    <section className="card flex flex-col gap-3">
      <h2 className="font-semibold">Comentarios</h2>
      <ul className="flex flex-col gap-2 text-sm">
        {d.comments.map((c) => (
          <li key={c.id} className="rounded-lg bg-slate-50 p-2.5">
            <div className="flex justify-between text-xs text-slate-500">
              <span>{c.author} · {new Date(c.created_at + 'Z').toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })}{c.pending && <Pending />}</span>
              {!c.pending && <button className="text-red-600" onClick={() => onDelete(c.id)}>Borrar</button>}
            </div>
            <p className="whitespace-pre-wrap pt-1">{c.text}</p>
          </li>
        ))}
        {d.comments.length === 0 && <li className="text-slate-400">Sin comentarios.</li>}
      </ul>
      <form className="flex gap-2" onSubmit={async (e) => { e.preventDefault(); if (text.trim()) { const t = text.trim(); setText(''); await onAdd(t) } }}>
        <input className="input" placeholder="Incidencias, observaciones…" value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} />
        <button className="btn" disabled={!text.trim()}>Enviar</button>
      </form>
    </section>
  )
}

function Assignees({ tid, matchId, current }: { tid: number; matchId: number; current: number[] }) {
  const members = useLoad(() => api.members(tid), [tid])
  const [ids, setIds] = useState<number[]>(current)
  const act = useAction()
  const toggle = async (id: number) => {
    const next = ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]
    const prev = ids
    setIds(next)
    if (!(await act.run(() => api.setAssignments(matchId, next)))) setIds(prev)
  }
  return (
    <section className="card flex flex-col gap-2">
      <h2 className="font-semibold">Planilleros asignados</h2>
      {members.data?.members.map((m) => (
        <label key={m.user_id} className="flex items-center gap-3 py-1">
          <input type="checkbox" className="h-5 w-5" checked={ids.includes(m.user_id)} onChange={() => toggle(m.user_id)} />
          <span>{m.name} <span className="text-sm text-slate-400">· {m.role === 'admin' ? 'organizador' : 'planillero'}</span></span>
        </label>
      ))}
      {members.data?.members.length === 1 && <p className="text-sm text-slate-400">Sumá planilleros desde la pestaña «Equipo de trabajo».</p>}
      <ErrorMsg msg={act.error || members.error} />
    </section>
  )
}

function Schedule({ matchId, scheduledAt, venue, onSaved }: { matchId: number; scheduledAt: string | null; venue: string | null; onSaved: () => Promise<void> }) {
  const [when, setWhen] = useState(scheduledAt?.slice(0, 16) ?? '')
  const [place, setPlace] = useState(venue ?? '')
  const act = useAction()
  return (
    <section className="card flex flex-col gap-2">
      <h2 className="font-semibold">Fecha y cancha</h2>
      <div className="grid grid-cols-2 gap-2">
        <input className="input" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
        <input className="input" placeholder="Cancha" maxLength={120} value={place} onChange={(e) => setPlace(e.target.value)} />
      </div>
      <ErrorMsg msg={act.error} />
      <button className="btn-ghost" disabled={act.busy}
        onClick={() => act.run(async () => { await api.setSchedule(matchId, when || null, place || null); await onSaved() })}>
        Guardar fecha y cancha
      </button>
    </section>
  )
}
