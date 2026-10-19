import { useCallback, useEffect, useRef, useState } from 'react'

export type DrawStep = { team_id: number; group: number }
export type Speed = 'slow' | 'normal' | 'fast'
/** Qué sale primero en cada paso: el equipo y después su grupo, o al revés. */
export type RevealOrder = 'team-first' | 'group-first'

/** Milisegundos que "gira" cada bolilla y que queda a la vista una vez revelada. */
const TIMES: Record<Speed, { spin: number; hold: number }> = {
  slow: { spin: 2000, hold: 1100 },
  normal: { spin: 1200, hold: 700 },
  fast: { spin: 450, hold: 250 },
}

/** Lo que se muestra del sorteo en curso: cada mitad gira (``done`` falso) hasta que se revela. */
export type Shown = {
  teamId: number; group: number
  teamText: string; teamDone: boolean
  groupText: string; groupDone: boolean
}

export const groupLetter = (i: number) => String.fromCharCode(65 + i)
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/**
 * Reproduce un sorteo ya resuelto, equipo por equipo, como en un sorteo de mundial: primero sale una
 * mitad (equipo o grupo), después la otra. ``onPlace`` se llama al revelarse el par completo.
 * ``skip`` completa lo que falta sin esperas; ``cancel`` corta. No respeta «reducir movimiento» a
 * propósito: el organizador pidió ver la animación.
 */
export function useDrawAnimation(onPlace: (teamId: number, group: number) => void) {
  const [shown, setShown] = useState<Shown | null>(null)
  const [running, setRunning] = useState(false)
  const flags = useRef({ skip: false, cancel: false })
  const place = useRef(onPlace)
  place.current = onPlace
  useEffect(() => () => { flags.current.cancel = true }, [])

  const play = useCallback(async (
    steps: DrawStep[], names: Map<number, string>, nGroups: number, speed: Speed, order: RevealOrder,
  ) => {
    const { spin, hold } = TIMES[speed]
    const allNames = steps.map((s) => names.get(s.team_id) ?? '')
    flags.current = { skip: false, cancel: false }
    const f = flags.current
    setRunning(true)
    const rand = {
      team: () => allNames[Math.floor(Math.random() * allNames.length)],
      group: () => `Grupo ${groupLetter(Math.floor(Math.random() * nGroups))}`,
    }

    for (const st of steps) {
      if (f.cancel) break
      if (!f.skip) {
        const finalText = { team: names.get(st.team_id) ?? '', group: `Grupo ${groupLetter(st.group)}` }
        const parts = order === 'team-first' ? (['team', 'group'] as const) : (['group', 'team'] as const)
        const cur: Shown = { teamId: st.team_id, group: st.group, teamText: '', teamDone: false, groupText: '', groupDone: false }
        for (const [i, part] of parts.entries()) {
          const duration = i === 0 ? spin : Math.round(spin * 0.7)
          for (const start = Date.now(); Date.now() - start < duration && !f.skip && !f.cancel; ) {
            setShown({ ...cur, [`${part}Text`]: rand[part]() })
            await sleep(70)
          }
          if (f.skip || f.cancel) break
          Object.assign(cur, { [`${part}Text`]: finalText[part], [`${part}Done`]: true })
          setShown({ ...cur })
          await sleep(i === 0 ? hold : 0)
        }
      }
      if (f.cancel) break
      place.current(st.team_id, st.group)
      if (!f.skip) await sleep(hold)
    }
    setShown(null)
    setRunning(false)
  }, [])

  return {
    shown, running, play,
    skip: () => { flags.current.skip = true },
    cancel: () => { flags.current.cancel = true },
  }
}
