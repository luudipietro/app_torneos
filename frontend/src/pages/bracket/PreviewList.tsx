import type { Entrant, KnockoutPreview } from '../../api'

function Side({ e, names }: { e: Entrant; names: Map<number, string> }) {
  return (
    <span className="flex min-w-0 flex-1 items-baseline gap-1.5 first:justify-end">
      <span className="truncate font-medium">{e.team_id != null ? names.get(e.team_id) : <i className="font-normal text-slate-500">{e.label}</i>}</span>
      <span className="shrink-0 text-xs text-slate-400">{(e.code ?? '').includes(':') ? '' : e.code}</span>
    </span>
  )
}

/** Quiénes juegan cada copa; los lugares que dependen de otra fase se muestran como «Ganador del partido…». */
export default function PreviewList({ preview, names }: { preview: KnockoutPreview; names: Map<number, string> }) {
  return (
    <>
      {preview.unplayed > 0 && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Faltan cerrar {preview.unplayed} partidos de la fase de grupos. Lo que ves es provisorio.
        </p>
      )}
      {preview.cups.map((c) => (
        <section key={c.name} className="card flex flex-col gap-2">
          <h3 className="font-bold text-green-700">{c.name}</h3>
          <p className="text-sm text-slate-500">
            {c.entrants.length} equipos · llave de {c.size}{c.byes > 0 && ` · ${c.byes} pasan directo (bye)`}
            {c.rounds < c.total_rounds && ` · se juega solo ${c.rounds === 1 ? 'una ronda' : `${c.rounds} rondas`}`}
          </p>
          {(c.pairs ?? []).length > 0 && (
            <div className="flex flex-col gap-1 text-sm">
              <h4 className="pt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Cruces de la primera ronda</h4>
              <ul className="flex flex-col gap-1">
                {(c.pairs ?? []).map((p, i) => (
                  <li key={i} className="flex items-center gap-2 rounded-lg bg-slate-50 px-2.5 py-1.5">
                    <Side e={p.home} names={names} />
                    <span className="text-slate-400">vs</span>
                    <Side e={p.away} names={names} />
                  </li>
                ))}
              </ul>
              {c.entrants.some((e) => e.bye) && (
                <p className="text-slate-500">Pasan directo: {c.entrants.filter((e) => e.bye).map((e) => (e.team_id != null ? names.get(e.team_id) : e.label)).join(', ')}</p>
              )}
            </div>
          )}
          <details className="text-sm">
            <summary className="cursor-pointer text-slate-500">Ver siembra completa</summary>
          <ol className="flex flex-col gap-1 pt-1">
            {c.entrants.map((e) => (
              <li key={e.seed} className="flex items-center gap-2">
                <span className="w-7 text-right text-slate-400">{e.seed}</span>
                {e.team_id != null ? (
                  <>
                    <span className="flex-1 truncate">{names.get(e.team_id)}</span>
                    <span className="text-slate-400">{e.position}º {e.group_name?.replace('Grupo ', '')}</span>
                    <span className="w-14 text-right tabular-nums text-slate-500">{e.points} pts</span>
                  </>
                ) : (
                  <span className="flex-1 truncate italic text-slate-500">{e.label}</span>
                )}
              </li>
            ))}
          </ol>
          </details>
        </section>
      ))}
    </>
  )
}
