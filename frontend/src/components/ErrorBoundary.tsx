import { Component, ReactNode } from 'react'

/** Evita la pantalla en blanco: si una pantalla falla, muestra el error y deja volver o recargar. */
export default class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { error: Error | null }> {
  state = { error: null as Error | null }
  static getDerivedStateFromError(error: Error) { return { error } }
  componentDidUpdate(prev: { resetKey?: string }) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null })
  }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="card m-4 flex flex-col gap-2">
        <h2 className="font-semibold text-red-700">Esta pantalla tuvo un error</h2>
        <p className="text-sm text-slate-600">{this.state.error.message}</p>
        <p className="text-sm text-slate-500">Si recién se actualizó la app, reiniciá el servidor (backend) y recargá la página.</p>
        <button className="btn self-start" onClick={() => location.reload()}>Recargar</button>
      </div>
    )
  }
}
