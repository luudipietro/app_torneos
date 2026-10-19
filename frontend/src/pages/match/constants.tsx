export const TYPES: Record<string, { icon: string; label: string }> = {
  goal: { icon: '⚽', label: 'Gol' },
  penalty_goal: { icon: '⚽', label: 'Gol de penal' },
  own_goal: { icon: '🥅', label: 'Gol en contra' },
  yellow: { icon: '🟨', label: 'Amarilla' },
  second_yellow: { icon: '🟨🟥', label: 'Doble amarilla' },
  red: { icon: '🟥', label: 'Roja' },
}

export const STATUS: Record<string, string> = {
  scheduled: 'Programado',
  in_progress: 'En juego',
  finished: 'Finalizado',
}

export const Pending = () => <span title="Pendiente de sincronizar" className="ml-1 text-amber-600">⏳</span>
