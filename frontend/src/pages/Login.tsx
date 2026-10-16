import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'
import { setMe } from '../offline/queue'
import { ErrorMsg, useAction } from '../ui'

export default function Login() {
  const nav = useNavigate()
  const [register, setRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const { error, busy, run } = useAction()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await run(async () => {
      const r = register ? await api.register(email, name, password) : await api.login(email, password)
      setToken(r.access_token)
      const me = await api.me()
      setMe({ id: me.id, name: me.name })
      nav('/')
    })
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 px-4">
      <h1 className="text-center text-2xl font-bold text-green-700">⚽ Torneos de Fútbol</h1>
      <form onSubmit={submit} className="card flex flex-col gap-3">
        <h2 className="font-semibold">{register ? 'Crear cuenta' : 'Ingresar'}</h2>
        {register && <input className="input" placeholder="Nombre" value={name} onChange={(e) => setName(e.target.value)} required />}
        <input className="input" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="input" type="password" placeholder="Contraseña (mín. 8)" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
        <ErrorMsg msg={error} />
        <button className="btn" disabled={busy}>{register ? 'Registrarme' : 'Entrar'}</button>
        <button type="button" className="text-sm text-slate-500" onClick={() => setRegister(!register)}>
          {register ? 'Ya tengo cuenta' : 'Crear una cuenta'}
        </button>
      </form>
    </div>
  )
}
