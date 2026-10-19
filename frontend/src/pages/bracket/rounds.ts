const ROUND_NAMES = ['Final', 'Semifinales', 'Cuartos de final', 'Octavos de final', 'Dieciseisavos de final']

/** Nombre de la ronda ``round`` (1 = primera) en una llave de ``total`` rondas. */
export const roundName = (round: number, total: number) => {
  const left = total - round
  return ROUND_NAMES[left] ?? `Ronda de ${2 ** (left + 1)}`
}
