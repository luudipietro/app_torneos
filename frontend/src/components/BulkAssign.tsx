import { useMemo, useState } from 'react'
import { api, Match, Stage } from '../api'
import { ErrorMsg, useAction, useLoad } from '../ui'

type Row = Match & { stageName: string; groupName: string | null }
const NO_VENUE = '__none__'

/**
 * Asignar planilleros en bloque a los partidos de cualquier etapa (grupos o llaves), filtrando por
 * etapa, fecha/ronda, grupo, cancha o «solo sin asignar». También permite poner la cancha en bloque.
 */
export default function BulkAssign({ tid, people }: { tid: number; people: { user_id: number; name: string }[] }) {
  const teams = useLoad(() => api.teams(tid), [tid])
  const all = useLoad(async () => {
    const stages = await api.stages(tid)
    const lists = await Promise.all(stages.map((s: Stage) => api.matches(s.id)))
    return stages.flatMap((s: Stage, i: number): Row[] =>
      lists[i].map((m) => ({ ...m, stageName: s.name, groupName: s.groups.find((g) => g.id === m.group_id)?.name ?? null })))
  }, [tid])
  const [person, setPerson] = useState('')
  const [stage, setStage] = useState('')
  const [round, setRound] = useState('')
  const [group, setGroup] = useState('')
  const [venue, setVenue] = useState('')
  const [onlyFree, setOnlyFree] = useState(false)
  const [newVenue, setNewVenue] = useState('')
  const [done, setDone] = useState('')
  const act = useAction()

  const rows = all.data ?? []
  const names = new Map((teams.data ?? []).map((t) => [t.id, t.name]))
  const inStage = rows.filter((m) => !stage || m.stageName === stage)
  const rounds = [...new Set(inStage.map((m) => m.round))].sort((a, b) => a - b)
  const groups = [...new Set(inStage.map((m) => m.groupName).filter((g): g is string => !!g))]
  const venues = [...new Set(rows.map((m) => m.venue).filter((v): v is string => !!v))].sort()
  const stageNames = [...new Set(rows.map((m) => m.stageName))]

  const picked = useMemo(
    () => inStage.filter((m) =>
      (!round || m.round === Number(round)) &&
      (!group || m.groupName === group) &&
      (!venue || (venue === NO_VENUE ? !m.venue : m.venue === venue)) &&
      (!onlyFree || m.assignee_ids.length === 0)),
    [inStage, round, group, venue, onlyFree],
  )
  const label = (m: Row) => `${m.groupName ?? m.stageName} · ${m.is_third_place ? '3er puesto' : `F${m.round}`} · ${m.home_team_id ? names.get(m.home_team_id) : 'A definir'} vs ${m.away_team_id ? names.get(m.away_team_id) : 'A definir'}${m.venue ? ` · ${m.venue}` : ''}`

  const assign = async () => {
    setDone('')
    if (picked.length && (await act.run(() => api.bulkAssign(tid, Number(person), picked.map((m) => m.id))))) {
      setDone(`Asignado a ${picked.length} partido${picked.length > 1 ? 's' : ''}.`)
      all.reload()
    }
  }
  const setVenueAll = async () => {
    setDone('')
    const v = newVenue.trim()
    if (picked.length && v && (await act.run(async () => { for (const m of picked) await api.setSchedule(m.id, m.scheduled_at, v) }))) {
      setDone(`Cancha «${v}» puesta en ${picked.length} partido${picked.length > 1 ? 's' : ''}.`)
      setNewVenue('')
      all.reload()
    }
  }

  return (
    <section className="card flex flex-col gap-3">
      <h2 className="font-semibold">Asignar partidos en bloque</h2>
      <p className="text-sm text-slate-500">
        Filtrá los partidos (grupos o llaves, por fecha, grupo o cancha) y asignáselos a una persona. También podés asignar uno por uno desde cada partido.
      </p>
      <select className="input" value={person} onChange={(e) => setPerson(e.target.value)}>
        <option value="">Persona…</option>
        {people.map((p) => <option key={p.user_id} value={p.user_id}>{p.name}</option>)}
      </select>
      <div className="grid gap-2 sm:grid-cols-2">
        <select className="input" value={stage} onChange={(e) => { setStage(e.target.value); setRound(''); setGroup('') }}>
          <option value="">Todas las etapas y copas</option>
          {stageNames.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
        <select className="input" value={round} onChange={(e) => setRound(e.target.value)}>
          <option value="">Todas las fechas / rondas</option>
          {rounds.map((r) => <option key={r} value={r}>Fecha / ronda {r}</option>)}
        </select>
        {groups.length > 0 && (
          <select className="input" value={group} onChange={(e) => setGroup(e.target.value)}>
            <option value="">Todos los grupos</option>
            {groups.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        )}
        <select className="input" value={venue} onChange={(e) => setVenue(e.target.value)}>
          <option value="">Todas las canchas</option>
          {venues.map((v) => <option key={v} value={v}>{v}</option>)}
          <option value={NO_VENUE}>Sin cancha</option>
        </select>
      </div>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={onlyFree} onChange={(e) => setOnlyFree(e.target.checked)} /> Solo los que todavía no tienen planillero</label>

      <details className="rounded-lg bg-slate-50 p-2 text-sm">
        <summary className="cursor-pointer font-medium">{picked.length} partido{picked.length === 1 ? '' : 's'} seleccionado{picked.length === 1 ? '' : 's'}</summary>
        <ul className="flex max-h-60 flex-col gap-1 overflow-y-auto pt-2 text-slate-600">
          {picked.map((m) => <li key={m.id} className="truncate">{label(m)}</li>)}
        </ul>
      </details>

      <ErrorMsg msg={act.error || all.error} />
      {done && <p className="rounded-lg bg-green-50 px-3 py-2 text-sm text-green-800">{done}</p>}
      <button className="btn" disabled={!person || picked.length === 0 || act.busy} onClick={assign}>
        Asignar {picked.length} partido{picked.length === 1 ? '' : 's'}
      </button>

      <div className="flex flex-col gap-2 border-t border-slate-100 pt-3">
        <h3 className="text-sm font-medium">Poner la cancha a los {picked.length} partidos seleccionados</h3>
        <div className="flex gap-2">
          <input className="input" placeholder="Nombre de la cancha" maxLength={120} value={newVenue} onChange={(e) => setNewVenue(e.target.value)} />
          <button className="btn-ghost shrink-0" disabled={!newVenue.trim() || picked.length === 0 || act.busy} onClick={setVenueAll}>Poner cancha</button>
        </div>
      </div>
    </section>
  )
}
