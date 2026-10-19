import type { Shown } from './useDrawAnimation'

function Ball({ title, text, done, tone }: { title: string; text: string; done: boolean; tone: 'slate' | 'green' }) {
  const color = done ? (tone === 'green' ? 'border-green-600 bg-green-600 text-white' : 'border-slate-700 bg-slate-800 text-white') : 'border-slate-300 bg-white text-slate-400'
  return (
    <div className="flex min-w-0 flex-1 flex-col items-center gap-1">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</span>
      <div key={done ? text : 'spin'} className={`flex min-h-20 w-full items-center justify-center rounded-2xl border-2 px-3 py-4 text-center text-2xl font-bold ${color} ${done ? 'draw-pop' : ''}`}>
        <span className="truncate">{text || '…'}</span>
      </div>
    </div>
  )
}

/** El "bombo": sale un equipo (o un grupo) y después el otro, como en un sorteo de mundial. */
export default function DrawStage({ shown, onSkip, onStop }: { shown: Shown | null; onSkip: () => void; onStop: () => void }) {
  return (
    <section className="card flex flex-col items-center gap-3 border-green-300 bg-green-50" aria-live="polite">
      <div className="text-4xl" aria-hidden>🎲</div>
      {shown ? (
        <div className="flex w-full items-center gap-3">
          <Ball title="Equipo" text={shown.teamText} done={shown.teamDone} tone="slate" />
          <span className="pt-5 text-2xl text-slate-400" aria-hidden>→</span>
          <Ball title="Grupo" text={shown.groupText} done={shown.groupDone} tone="green" />
        </div>
      ) : (
        <p className="text-sm text-slate-500">Preparando el sorteo…</p>
      )}
      <div className="flex gap-2">
        <button className="btn-ghost" onClick={onSkip}>Mostrar todo ya</button>
        <button className="btn-ghost" onClick={onStop}>Detener</button>
      </div>
    </section>
  )
}
