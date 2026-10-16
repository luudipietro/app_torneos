import type { Stats } from '../api'

const REASON = { red: '🟥 Expulsión', yellows: '🟨 Amarillas' } as const

function Card({ title, children, empty }: { title: string; children: React.ReactNode; empty?: string }) {
  return (
    <section className="card flex flex-col gap-2">
      <h3 className="font-semibold">{title}</h3>
      {empty ? <p className="text-sm text-slate-400">{empty}</p> : children}
    </section>
  )
}

const Th = ({ children, right }: { children?: React.ReactNode; right?: boolean }) => (
  <th className={`py-1 font-normal text-slate-400 ${right ? 'text-right' : 'text-left'}`}>{children}</th>
)

/** Estadísticas del torneo: se usa en la pestaña del organizador y en la vista pública. */
export default function StatsView({ stats: s }: { stats: Stats }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-2 text-center">
        {[['Partidos', s.matches_played], ['Goles', s.total_goals], ['Goles por partido', s.goals_per_match]].map(([label, v]) => (
          <div key={label} className="card !p-3">
            <div className="text-2xl font-bold text-green-700 tabular-nums">{v}</div>
            <div className="text-xs text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      <Card title="⚽ Goleadores" empty={s.scorers.length === 0 ? 'Todavía no hay goles cargados.' : undefined}>
        <table className="w-full text-sm">
          <thead><tr><Th>#</Th><Th>Jugador</Th><Th right>Goles</Th></tr></thead>
          <tbody>
            {s.scorers.map((r) => (
              <tr key={r.player_id} className="border-t border-slate-100">
                <td className="w-8 py-1.5 text-slate-400">{r.rank}</td>
                <td><div className="font-medium">{r.name}</div><div className="text-xs text-slate-500">{r.team_name}</div></td>
                <td className="text-right font-bold tabular-nums">{r.goals}{r.penalties > 0 && <span className="ml-1 text-xs font-normal text-slate-400">({r.penalties} de penal)</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="🧤 Valla menos vencida" empty={s.defense.length === 0 ? 'Se completa cuando terminan los primeros partidos.' : undefined}>
        <table className="w-full text-sm">
          <thead><tr><Th>#</Th><Th>Equipo</Th><Th right>PJ</Th><Th right>GC</Th><Th right>Prom.</Th><Th right>Vallas</Th></tr></thead>
          <tbody>
            {s.defense.map((r) => (
              <tr key={r.team_id} className="border-t border-slate-100">
                <td className="w-8 py-1.5 text-slate-400">{r.rank}</td>
                <td className="font-medium">{r.team_name}</td>
                <td className="text-right tabular-nums">{r.played}</td>
                <td className="text-right tabular-nums">{r.goals_against}</td>
                <td className="text-right tabular-nums">{r.average.toFixed(2)}</td>
                <td className="text-right tabular-nums">{r.clean_sheets}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-slate-400">GC: goles en contra · Vallas: partidos sin recibir goles</p>
      </Card>

      <Card title="🟨🟥 Tarjetas" empty={s.cards.length === 0 ? 'Sin tarjetas por ahora.' : undefined}>
        <table className="w-full text-sm">
          <thead><tr><Th>Jugador</Th><Th right>🟨</Th><Th right>🟥</Th></tr></thead>
          <tbody>
            {s.cards.map((r) => (
              <tr key={r.player_id} className="border-t border-slate-100">
                <td className="py-1.5"><div className="font-medium">{r.name}</div><div className="text-xs text-slate-500">{r.team_name}</div></td>
                <td className="text-right tabular-nums">{r.yellow}</td>
                <td className="text-right tabular-nums">{r.red}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="🤝 Fair play" empty={s.fair_play.every((f) => f.points === 0) ? 'Todos los equipos sin sanciones.' : undefined}>
        <table className="w-full text-sm">
          <thead><tr><Th>Equipo</Th><Th right>🟨</Th><Th right>🟥</Th><Th right>Pts</Th></tr></thead>
          <tbody>
            {s.fair_play.map((r) => (
              <tr key={r.team_id} className="border-t border-slate-100">
                <td className="py-1.5 font-medium">{r.team_name}</td>
                <td className="text-right tabular-nums">{r.yellow}</td>
                <td className="text-right tabular-nums">{r.red}</td>
                <td className="text-right font-bold tabular-nums">{r.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-slate-400">Amarilla = 1 punto, roja = 3. Gana el que menos suma.</p>
      </Card>

      <Card title="⛔ Suspendidos para la próxima fecha" empty={s.suspensions.length === 0 ? 'No hay jugadores suspendidos.' : undefined}>
        <ul className="flex flex-col gap-1.5 text-sm">
          {s.suspensions.map((x) => (
            <li key={x.player_id} className="flex items-center justify-between gap-2">
              <span><b>{x.player_name}</b> <span className="text-slate-400">· {x.team_name}</span></span>
              <span className="text-right text-slate-600">{REASON[x.reason]} · {x.remaining} partido{x.remaining > 1 ? 's' : ''}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
