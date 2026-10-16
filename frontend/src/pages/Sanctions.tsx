import { api } from '../api'
import { ErrorMsg, useLoad } from '../ui'

export default function Sanctions({ tid }: { tid: number }) {
  const { data, error } = useLoad(() => api.suspensions(tid), [tid])
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-slate-500">Jugadores que no pueden jugar el próximo partido de su equipo (según tarjetas de partidos cerrados).</p>
      <ErrorMsg msg={error} />
      <ul className="flex flex-col gap-2">
        {data?.map((s) => (
          <li key={s.player_id} className="card flex items-center justify-between">
            <div>
              <div className="font-semibold">{s.player_name}</div>
              <div className="text-sm text-slate-500">{s.team_name}</div>
            </div>
            <div className="text-right text-sm">
              <div>{s.reason === 'red' ? '🟥 Expulsión' : '🟨 Acumulación de amarillas'}</div>
              <div className="font-semibold text-red-700">{s.remaining} partido{s.remaining > 1 ? 's' : ''}</div>
            </div>
          </li>
        ))}
        {data?.length === 0 && <li className="card text-center text-slate-500">No hay jugadores suspendidos.</li>}
      </ul>
    </div>
  )
}
