import { useEffect, useState } from 'react'
import { api, Cup, KnockoutConfig, KnockoutPreview } from '../../api'
import { ErrorMsg, useAction, useLoad, usePersistentState } from '../../ui'
import PhaseEditor from './PhaseEditor'
import PreviewList from './PreviewList'

type Draft = { cups: Cup[]; picked: number | null; third: boolean; avoid: boolean; auto?: boolean }
const blank = (name: string): Cup => ({ name, positions: [], extra: [], from_winners: [], from_losers: [], max_rounds: null, third_place: null, avoid_same_group: null })

/** Arma las llaves: parte de un formato sugerido (o de cero) y se puede personalizar copa por copa. */
export default function Setup({ tid, names, maxPosition, onDone }: { tid: number; names: Map<number, string>; maxPosition: number; onDone: () => void }) {
  const plans = useLoad(() => api.knockoutPlans(tid), [tid])
  // el borrador se guarda en el navegador hasta crear las llaves
  const [draft, setDraft, clearDraft] = usePersistentState<Draft>(`draft:knockout:${tid}`, { cups: [], picked: null, third: true, avoid: true, auto: true })
  const { cups, picked, third, avoid } = draft
  const auto = draft.auto ?? true
  const [loaded, setLoaded] = useState(false) // ya se consultó el formato guardado en el servidor
  const [server, setServer] = useState<KnockoutConfig | null>(null) // formato guardado en el torneo
  const [editing, setEditing] = useState(true) // sin formato guardado se edita directo; con formato guardado, solo tras confirmar
  const [asking, setAsking] = useState(false)
  const [msg, setMsg] = useState('')
  const setCups = (f: Cup[] | ((c: Cup[]) => Cup[])) => setDraft((d) => ({ ...d, cups: typeof f === 'function' ? f(d.cups) : f }))
  const setPicked = (v: number | null) => setDraft((d) => ({ ...d, picked: v }))
  const setThird = (v: boolean) => setDraft((d) => ({ ...d, third: v }))
  const setAvoid = (v: boolean) => setDraft((d) => ({ ...d, avoid: v }))
  const setAuto = (v: boolean) => setDraft((d) => ({ ...d, auto: v }))
  const [base, setBase] = useState<KnockoutPreview | null>(null) // la misma config con cruces por siembra: da los equipos para armar cruces a mano
  const [preview, setPreview] = useState<KnockoutPreview | null>(null)
  const [previewError, setPreviewError] = useState('')
  const act = useAction()

  // el formato guardado en el torneo manda sobre el borrador del navegador y queda protegido contra ediciones accidentales
  const toDraft = (c: KnockoutConfig): Draft => ({ cups: c.cups, picked: c.picked, third: c.third_place, avoid: c.avoid_same_group, auto: c.auto_create })
  useEffect(() => {
    api.knockoutConfig(tid)
      .then((c) => { if (c) { setServer(c); setDraft(toDraft(c)); setEditing(false) } })
      .catch(() => {})
      .finally(() => setLoaded(true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tid, setDraft])

  const current: KnockoutConfig = { cups, third_place: third, avoid_same_group: avoid, auto_create: auto, picked }
  const dirty = !server || JSON.stringify(current) !== JSON.stringify(server)
  const save = () => act.run(async () => {
    const c = await api.saveKnockoutConfig(tid, current)
    setServer(c)
    setEditing(false)
    setMsg('Formato guardado. Es el que se usa para crear las llaves.')
  })
  const discard = () => {
    if (!server) return
    setDraft(toDraft(server))
    setEditing(false)
    setMsg('')
  }

  // arranca con el primer formato sugerido
  useEffect(() => {
    if (loaded && plans.data?.length && picked === null && cups.length === 0) setDraft((d) => ({ ...d, picked: 0, cups: plans.data![0].cups }))
  }, [loaded, plans.data, picked, cups.length, setDraft])

  // vista previa con las posiciones actuales, apenas se deja de editar
  const key = JSON.stringify([cups, third, avoid])
  useEffect(() => {
    if (cups.length === 0) { setPreview(null); return }
    let stale = false
    const timer = setTimeout(() => {
      if (cups.some((c) => c.pairing === 'manual')) {
        const seeded = cups.map((c) => (c.pairing === 'manual' ? { ...c, pairing: 'seeded' as const, manual_pairs: [] } : c))
        api.knockoutPreview(tid, { cups: seeded, third_place: third, avoid_same_group: avoid }).then((p) => { if (!stale) setBase(p) }).catch(() => {})
      } else setBase(null)
      api.knockoutPreview(tid, { cups, third_place: third, avoid_same_group: avoid })
        .then((p) => { if (!stale) { setPreview(p); setPreviewError('') } })
        .catch((e) => { if (!stale) { setPreview(null); setPreviewError(e.message) } })
    }, 300)
    return () => { stale = true; clearTimeout(timer) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tid])

  const patch = (i: number, p: Partial<Cup>) =>
    setCups((cs) => cs.map((c, j) => {
      if (j === i) return { ...c, ...p }
      if (!p.name) return c
      const old = cs[i].name // al renombrar una copa se actualizan las que la usan como origen
      const swap = (l?: string[]) => l?.map((n) => (n === old ? p.name! : n))
      return { ...c, from_winners: swap(c.from_winners), from_losers: swap(c.from_losers) }
    }))
  const remove = (i: number) =>
    setCups((cs) => {
      const gone = cs[i].name
      return cs.filter((_, j) => j !== i).map((c) => ({
        ...c, from_winners: c.from_winners?.filter((n) => n !== gone), from_losers: c.from_losers?.filter((n) => n !== gone),
      }))
    })
  const move = (i: number, dir: -1 | 1) =>
    setCups((cs) => {
      const j = i + dir
      if (j < 0 || j >= cs.length) return cs
      const next = [...cs]
      ;[next[i], next[j]] = [next[j], next[i]]
      return next
    })
  const add = () => setCups((cs) => [...cs, blank(`Copa ${cs.length + 1}`)])

  if (!plans.data) return <ErrorMsg msg={plans.error} />

  return (
    <div className="flex flex-col gap-4">
      <section className="card flex flex-col gap-3">
        <h2 className="font-semibold">Clasificación a las llaves</h2>
        {editing
          ? <p className="text-sm text-slate-500">Elegí un formato para empezar y después ajustalo como quieras. No se aplica hasta que lo guardes.</p>
          : <p className="rounded-lg bg-green-50 px-3 py-2 text-sm text-green-800">✔ Formato guardado: es el que se usa para crear las llaves{auto ? ' (se crean solas al cerrar el último partido de grupos)' : ''}. Para cambiarlo tenés que confirmar la edición.</p>}
        <fieldset disabled={!editing} className={`flex flex-col gap-3 ${editing ? '' : 'opacity-70'}`}>
        <div className="flex flex-col gap-2">
          {plans.data.map((p, i) => (
            <label key={p.label} className={`flex items-center gap-3 rounded-lg border p-3 text-sm ${picked === i ? 'border-green-600 bg-green-50' : 'border-slate-200'}`}>
              <input type="radio" checked={picked === i} onChange={() => { setPicked(i); setCups(p.cups) }} />
              <span>{p.label}</span>
            </label>
          ))}
          <label className={`flex items-center gap-3 rounded-lg border p-3 text-sm ${picked === -1 ? 'border-green-600 bg-green-50' : 'border-slate-200'}`}>
            <input type="radio" checked={picked === -1} onChange={() => { setPicked(-1); setCups([{ ...blank('Copa de Oro'), positions: [1] }]) }} />
            <span>Armar desde cero</span>
          </label>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={third} onChange={(e) => setThird(e.target.checked)} /> Partido por el 3er puesto (en todas las copas)</label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={avoid} onChange={(e) => setAvoid(e.target.checked)} /> Evitar cruces entre equipos del mismo grupo</label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> Crear las llaves automáticamente al cerrar el último partido de grupos</label>
        </fieldset>
        {msg && <p className="text-xs text-slate-500">{msg}</p>}
        {!editing && !asking && <button className="btn-ghost self-start" onClick={() => setAsking(true)}>Editar formato…</button>}
        {!editing && asking && (
          <div className="flex flex-col gap-2 rounded-lg border-2 border-amber-400 bg-amber-50 p-3" role="alertdialog">
            <p className="font-semibold">¿Querés modificar el formato guardado?</p>
            <p className="text-sm text-amber-900">Los cambios no se aplican hasta que aprietes «Guardar formato». Si no guardás, sigue valiendo el formato actual.</p>
            <div className="flex gap-2">
              <button className="btn" onClick={() => { setAsking(false); setEditing(true); setMsg('') }}>Sí, editar</button>
              <button className="btn-ghost" onClick={() => setAsking(false)}>Cancelar</button>
            </div>
          </div>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="font-semibold">Copas y fases</h2>
        <fieldset disabled={!editing} className={`flex flex-col gap-2 ${editing ? '' : 'opacity-70'}`}>
        {cups.map((c, i) => (
          <details key={i} className="card" open={picked === -1 || cups.length === 1}>
            <summary className="cursor-pointer font-medium">{i + 1}. {c.name || 'Sin nombre'}</summary>
            <PhaseEditor cup={c} others={cups.filter((_, j) => j !== i).map((x) => x.name)} maxPosition={maxPosition}
              entrants={base?.cups.find((x) => x.name === c.name)?.entrants} seeded={base?.cups.find((x) => x.name === c.name)?.pairs ?? []} names={names}
              onChange={(p) => patch(i, p)} onRemove={() => remove(i)} onMove={(d) => move(i, d)} />
          </details>
        ))}
        {cups.length < 8 && <button className="btn-ghost self-start" onClick={add}>+ Agregar copa o fase</button>}
        </fieldset>
        {editing && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <button className="btn" disabled={act.busy || cups.length === 0 || !dirty} onClick={save}>Guardar formato</button>
            {server && <button className="btn-ghost" onClick={discard}>Descartar cambios</button>}
            {server && dirty && <span className="text-sm text-amber-700">Hay cambios sin guardar.</span>}
            {!server && <span className="text-sm text-amber-700">Todavía no hay un formato guardado.</span>}
          </div>
        )}
      </section>

      <ErrorMsg msg={previewError || act.error} />
      {preview && (
        <>
          <PreviewList preview={preview} names={names} />
          {preview.unplayed > 0 && <p className="text-sm text-slate-500">Los cruces se actualizan con cada resultado.{server ? (auto ? ' Las llaves se crean solas al cerrar el último partido de grupos.' : ' Las llaves se crean cuando apretás el botón, al terminar los grupos.') : ' Guardá el formato para que se pueda crear solo.'}</p>}
          <button className="btn" disabled={act.busy || preview.unplayed > 0}
            onClick={async () => { if (await act.run(() => api.createKnockout(tid, { cups, third_place: third, avoid_same_group: avoid }))) { clearDraft(); onDone() } }}>
            Crear llaves
          </button>
        </>
      )}
    </div>
  )
}
