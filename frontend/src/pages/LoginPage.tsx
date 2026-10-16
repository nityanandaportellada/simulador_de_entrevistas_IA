import { useState, type FormEvent } from 'react'
import { ArrowRight, BarChart3, BookOpenText, GraduationCap, LockKeyhole, Mail } from 'lucide-react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { useAuth } from '../contexts/AuthContext'
import { ApiError } from '../services/api'

export function LoginPage() {
  const { autenticado, usuario, login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  if (autenticado && usuario) {
    return (
      <Navigate
        to={usuario.perfil === 'administrador' ? '/admin' : '/dashboard'}
        replace
      />
    )
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setErro('')
    setEnviando(true)

    try {
      const atual = await login({ email, senha })
      navigate(atual.perfil === 'administrador' ? '/admin' : '/dashboard')
    } catch (error) {
      setErro(error instanceof ApiError ? error.message : 'Não foi possível entrar.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-hero">
        <Brand />
        <div className="auth-hero__copy">
          <h1>
            Prepare hoje as oportunidades <span>de amanhã</span>
          </h1>
          <p>
            Sistema da Faculdade de Educação Superior do Paraná para prática
            e avaliação de entrevistas por escrito.
          </p>

          <div className="feature-list">
            <div>
              <BookOpenText />
              <span><strong>Pratique com cenários reais</strong>Desenvolva suas respostas em situações acadêmicas e profissionais.</span>
            </div>
            <div>
              <BarChart3 />
              <span><strong>Receba feedback estruturado</strong>Avaliação automatizada com critérios claros.</span>
            </div>
            <div>
              <GraduationCap />
              <span><strong>Acompanhe sua evolução</strong>Visualize seu progresso e seus pontos de desenvolvimento.</span>
            </div>
          </div>
        </div>
        <div className="auth-hero__signature">Educação que conecta futuros</div>
      </section>

      <section className="auth-card-wrap">
        <form className="auth-card" onSubmit={submit}>
          <Brand />
          <div>
            <h2>Entrar na sua conta</h2>
            <p>Acesse para continuar suas simulações.</p>
          </div>

          {erro && <div className="alert alert--error">{erro}</div>}

          <label className="field">
            <span>E-mail</span>
            <div className="input-with-icon">
              <Mail size={18} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
              />
            </div>
          </label>

          <label className="field">
            <span>Senha</span>
            <div className="input-with-icon">
              <LockKeyhole size={18} />
              <input
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                placeholder="Sua senha"
                minLength={8}
                required
              />
            </div>
          </label>

          <button className="button button--primary button--full" disabled={enviando}>
            {enviando ? 'Entrando...' : 'Entrar'} <ArrowRight size={18} />
          </button>

          <div className="auth-divider">Ainda não tem uma conta?</div>

          <Link className="button button--outline button--full" to="/cadastro">
            Criar conta
          </Link>
        </form>
      </section>
    </div>
  )
}
