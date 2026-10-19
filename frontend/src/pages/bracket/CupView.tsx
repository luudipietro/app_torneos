import { api, Match, Stage } from '../../api'
import { ErrorMsg, useLoad } from '../../ui'
import { CupBracket } from './CupBracket'

export default function CupView({ stage, names, tid, admin, meId }: { stage: Stage; names: Map<number, string>; tid: number; admin: boolean; meId: number }) {
  const matches = useLoad(() => api.matches(stage.id), [stage.id])
  const rounds = Number(stage.config.rounds ?? 1)
  return (
    <>
      <ErrorMsg msg={matches.error} />
      <CupBracket
        name={stage.name}
        rounds={rounds}
        totalRounds={Number(stage.config.total_rounds ?? rounds)}
        matches={matches.data ?? []}
        names={names}
        hrefFor={(m) => ((admin || (m as Match).assignee_ids?.includes(meId)) ? `/t/${tid}/partido/${m.id}` : null)}
      />
    </>
  )
}
