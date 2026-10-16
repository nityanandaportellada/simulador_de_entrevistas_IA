import { useState, type FormEvent } from 'react'
import { ArrowRight, LockKeyhole, Mail, UserRound } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { cadastrar } from '../services/authService'
import { ApiError } from '../services/api'

export function CadastroPage() {
  const navigate = useNavigate()
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setErro('')

    if (senha !== confirmar) {
      setErro('As senhas não conferem.')
      return
    }

    setEnviando(true)
    try {
      await cadastrar({ nome, email, senha })
      navigate('/login', { state: { cadastroOk: true } })
    } catch (error) {
      setErro(error instanceof ApiError ? error.message : 'Não foi possível criar a conta.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="auth-page auth-page--reverse">
      <section className="auth-card-wrap">
        <form className="auth-card" onSubmit={submit}>
          <Brand />
          <div>
            <h2>Criar conta</h2>
            <p>Cadastre-se para iniciar suas entrevistas simuladas.</p>
          </div>

          {erro && <div className="alert alert--error">{erro}</div>}

          <label className="field">
            <span>Nome completo</span>
            <div className="input-with-icon">
              <UserRound size={18} />
              <input value={nome} onChange={(e) => setNome(e.target.value)} required minLength={2} />
            </div>
          </label>

          <label className="field">
            <span>E-mail</span>
            <div className="input-with-icon">
              <Mail size={18} />
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
          </label>

          <label className="field">
            <span>Senha</span>
            <div className="input-with-icon">
              <LockKeyhole size={18} />
              <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required minLength={8} />
            </div>
          </label>

          <label className="field">
            <span>Confirmar senha</span>
            <div className="input-with-icon">
              <LockKeyhole size={18} />
              <input type="password" value={confirmar} onChange={(e) => setConfirmar(e.target.value)} required minLength={8} />
            </div>
          </label>

          <button className="button button--primary button--full" disabled={enviando}>
            {enviando ? 'Criando...' : 'Criar conta'} <ArrowRight size={18} />
          </button>

          <div className="auth-divider">Já tem uma conta?</div>
          <Link to="/login" className="button button--outline button--full">Entrar</Link>
        </form>
      </section>

      <section className="auth-hero">
        <Brand />
        <div className="auth-hero__copy">
          <h1>Comece sua <span>preparação hoje</span></h1>
          <p>
            Pratique entrevistas por escrito, desenvolva sua comunicação e
            acompanhe sua evolução com feedback estruturado.
          </p>
        </div>
        <div className="auth-hero__signature">Educação que conecta futuros</div>
      </section>
    </div>
  )
}
