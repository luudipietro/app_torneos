import { useMemo } from 'react'
import { api, DrawResult, Team } from '../../api'
import { ErrorMsg, useAction, useLoad, usePersistentState } from '../../ui'
import DrawStage from './DrawStage'
import TeamPicker from './TeamPicker'
import { groupLetter, RevealOrder, Speed, useDrawAnimation } from './useDrawAnimation'

type Placed = { team_id: number; group: number }
/** Borrador del sorteo: se guarda en el navegador hasta confirmarlo, para no perderlo al cambiar de pestaña. */
type Draft = { n: number; double: boolean; speed: Speed; order: RevealOrder; placed: Placed[] }
const EMPTY: Draft = { n: 0, double: false, speed: 'normal', order: 'team-first', placed: [] }

/** Armado de grupos: a mano, sorteando (con animación) o mezclando ambas cosas. */
export default function DrawBoard({ tid, teams, onDone }: { tid: number; teams: Team[]; onDone: () => void }) {
  const enough = teams.length >= 4
  const layouts = useLoad(() => (enough ? api.layouts(tid) : Promise.resolve([])), [tid, teams.length])
  const [draft, setDraft, clearDraft] = usePersistentState<Draft>(`draft:groups:${tid}`, EMPTY)
  const { n, double, speed, order } = draft
  const ids = new Set(teams.map((t) => t.id))
  const placed = draft.placed.filter((p) => ids.has(p.team_id) && p.group < (n || 99))
  const setN = (v: number) => setDraft((d) => ({ ...d, n: v }))
  const setDouble = (v: boolean) => setDraft((d) => ({ ...d, double: v }))
  const setSpeed = (v: Speed) => setDraft((d) => ({ ...d, speed: v }))
  const setOrder = (v: RevealOrder) => setDraft((d) => ({ ...d, order: v }))
  const setPlaced = (f: Placed[] | ((p: Placed[]) => Placed[])) =>
    setDraft((d) => ({ ...d, placed: typeof f === 'function' ? f(d.placed) : f }))
  const act = useAction()
  const sel = n || layouts.data?.[0]?.n_groups || 0
  const sizes = layouts.data?.find((l) => l.n_groups === sel)?.sizes ?? []

  const put = (team_id: number, group: number | null) =>
    setPlaced((p) => [...p.filter((x) => x.team_id !== team_id), ...(group === null ? [] : [{ team_id, group }])])
  const anim = useDrawAnimation((id, g) => put(id, g))

  const names = useMemo(() => new Map(teams.map((t) => [t.id, t.name])), [teams])
  const byId = useMemo(() => new Map(teams.map((t) => [t.id, t])), [teams])
  const groupOf = new Map(placed.map((p) => [p.team_id, p.group]))
  const pool = teams.filter((t) => !groupOf.has(t.id)).sort((a, b) => a.name.localeCompare(b.name))
  const groups = Array.from({ length: sel }, (_, i) => placed.filter((p) => p.group === i).map((p) => p.team_id))
  const lastPlaced = anim.running ? placed[placed.length - 1]?.team_id : null
  const busy = act.busy || anim.running

  const pick = (value: number) => {
    if (placed.length && !confirm('Cambiar la cantidad de grupos borra los equipos ya ubicados. ¿Seguir?')) return
    setPlaced([])
    setN(value)
  }

  /** Sortea (con animación) los equipos que faltan; con ``all`` empieza de cero. */
  const run = async (all: boolean) => {
    const fixed: Record<number, number> = all ? {} : Object.fromEntries(placed.map((p) => [p.team_id, p.group]))
    if (all) setPlaced([])
    const out: { r?: DrawResult } = {}
    if (!(await act.run(async () => { out.r = await api.drawGroups(tid, { n_groups: sel, fixed }) })) || !out.r) return
    await anim.play(out.r.steps, names, sel, speed, order)
  }

  const confirmDraw = async () => {
    if (await act.run(() => api.createGroups(tid, { groups, double_round: double }))) {
      clearDraft()
      onDone()
    }
  }

  if (!enough) return <p className="card text-slate-500">Cargá al menos 4 equipos para hacer el sorteo.</p>
  const tooSmall = groups.some((g) => g.length < 2)
  const ready = pool.length === 0 && !anim.running && sel > 0 && !tooSmall

  return (
    <div className="flex flex-col gap-4">
      <section className="card flex flex-col gap-3">
        <h2 className="font-semibold">Grupos ({teams.length} equipos)</h2>
        <div className="flex flex-wrap gap-2">
          {layouts.data?.map((l) => (
            <button
              key={l.n_groups}
              disabled={busy}
              onClick={() => pick(l.n_groups)}
              className={`rounded-lg border px-3 py-2 text-sm ${sel === l.n_groups ? 'border-green-600 bg-green-50 font-semibold' : 'border-slate-200'}`}
            >
              {l.n_groups} {l.n_groups === 1 ? 'grupo' : 'grupos'} · {l.balanced ? `de ${l.sizes[0]}` : l.sizes.join('/')}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={double} onChange={(e) => setDouble(e.target.checked)} /> Ida y vuelta
        </label>
        <p className="text-sm text-slate-500">
          Ubicá equipos a mano con el selector de cada uno, sorteá todos, o fijá algunos y sorteá solo los que faltan.
          Los <b>cabezas de serie</b> (marcados «Serie 1», «Serie 2»… en la pestaña Equipos; el número es la prioridad,
          1 = el mejor) salen primero y se reparten uno por grupo. El borrador se guarda hasta que lo confirmes.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn" disabled={busy || !sel} onClick={() => run(false)}>
            🎲 {placed.length ? `Sortear los ${pool.length} que faltan` : 'Sortear todos'}
          </button>
          {placed.length > 0 && pool.length === 0 && (
            <button className="btn-ghost" disabled={busy} onClick={() => run(true)}>Volver a sortear todo</button>
          )}
          {placed.length > 0 && <button className="btn-ghost" disabled={busy} onClick={() => setPlaced([])}>Limpiar</button>}
          <label className="ml-auto flex items-center gap-2 text-sm text-slate-600">
            Sale primero
            <select className="rounded-lg border border-slate-300 bg-white px-2 py-1.5" value={order} disabled={anim.running} onChange={(e) => setOrder(e.target.value as RevealOrder)}>
              <option value="team-first">el equipo</option>
              <option value="group-first">el grupo</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            Velocidad
            <select className="rounded-lg border border-slate-300 bg-white px-2 py-1.5" value={speed} disabled={anim.running} onChange={(e) => setSpeed(e.target.value as Speed)}>
              <option value="slow">Lenta</option>
              <option value="normal">Normal</option>
              <option value="fast">Rápida</option>
            </select>
          </label>
        </div>
        <ErrorMsg msg={layouts.error || act.error} />
      </section>

      {anim.running && <DrawStage shown={anim.shown} onSkip={anim.skip} onStop={anim.cancel} />}

      {pool.length > 0 && (
        <section className="card flex flex-col gap-2">
          <h3 className="font-semibold">Sin grupo ({pool.length})</h3>
          <ul className="grid gap-2 sm:grid-cols-2">
            {pool.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-1.5 text-sm">
                <span className="truncate">{t.name}{t.seed != null && <span className="ml-1 text-xs text-amber-700" title={`Cabeza de serie ${t.seed}`}>Serie {t.seed}</span>}</span>
                <TeamPicker value={null} nGroups={sel} disabled={busy} onChange={(g) => put(t.id, g)} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {groups.map((ids, i) => {
          const hot = !!anim.shown?.groupDone && anim.shown.group === i
          return (
            <section key={i} className={`card flex flex-col gap-2 transition-shadow ${hot ? 'ring-2 ring-green-500' : ''}`}>
              <h3 className="flex items-baseline justify-between font-bold text-green-700">
                Grupo {groupLetter(i)}
                <span className="text-xs font-normal text-slate-400">{ids.length}{sizes[i] ? ` de ${sizes[i]}` : ''}</span>
              </h3>
              <ul className="flex min-h-10 flex-col gap-1.5">
                {ids.map((id) => (
                  <li key={id} className={`flex items-center justify-between gap-2 text-sm ${lastPlaced === id ? 'draw-pop font-bold' : ''}`}>
                    <span className="truncate">{names.get(id)}{byId.get(id)?.seed != null && <span className="ml-1 text-xs text-amber-700" title="Cabeza de serie">Serie {byId.get(id)?.seed}</span>}</span>
                    <TeamPicker value={i} nGroups={sel} disabled={busy} onChange={(g) => put(id, g)} />
                  </li>
                ))}
                {ids.length === 0 && <li className="text-sm text-slate-300">Vacío</li>}
              </ul>
              {ids.length === 1 && !anim.running && <p className="text-xs text-amber-700">Necesita al menos 2 equipos.</p>}
            </section>
          )
        })}
      </div>

      <button className="btn" disabled={!ready || busy} onClick={confirmDraw}>Confirmar grupos y generar fixture</button>
      {pool.length > 0 && !anim.running && <p className="text-center text-sm text-slate-400">Faltan ubicar {pool.length} equipos.</p>}
    </div>
  )
}
