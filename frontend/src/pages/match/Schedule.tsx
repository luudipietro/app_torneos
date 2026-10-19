import { useState } from 'react'
import { api } from '../../api'
import { ErrorMsg, useAction } from '../../ui'

export default function Schedule({ matchId, scheduledAt, venue, onSaved }: { matchId: number; scheduledAt: string | null; venue: string | null; onSaved: () => Promise<void> }) {
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
