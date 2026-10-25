
import { useEffect, useState, type FormEvent } from 'react'
import { apiGet, apiPut } from '../services/api'

type Configuracao = {
  limite_usuario_dia: number
  limite_global_dia: number
  limite_entrevista: number
  retencao_dias: number
  personalizada: boolean
  alterado_em_utc: string | null
  alterado_por: number | null
}
type Campo = 'limite_usuario_dia' | 'limite_global_dia' | 'limite_entrevista' | 'retencao_dias'

const campos: { nome: Campo; titulo: string; explicacao: string; minimo: number; maximo: number }[] = [
  { nome: 'limite_usuario_dia', titulo: 'Chamadas por estudante/dia', explicacao: 'Limite individual diário em UTC.', minimo: 1, maximo: 100000 },
  { nome: 'limite_global_dia', titulo: 'Chamadas globais/dia', explicacao: 'Cota diária conjunta de todo o sistema.', minimo: 1, maximo: 100000 },
  { nome: 'limite_entrevista', titulo: 'Chamadas por entrevista', explicacao: 'Limite acumulado mesmo após limpeza de logs.', minimo: 1, maximo: 100000 },
  { nome: 'retencao_dias', titulo: 'Retenção de registros (dias)', explicacao: 'Preserva o consumo acumulado mesmo após excluir registros detalhados.', minimo: 30, maximo: 365 }
]

function mensagem(erro: unknown) {
  return erro instanceof Error ? erro.message : 'Falha ao consultar as configurações.'
}

export function ConfiguracaoIA({ aoSalvar }: { aoSalvar: () => void }) {
  const [aberto, setAberto] = useState(false)
  const [dados, setDados] = useState<Configuracao | null>(null)
  const [formulario, setFormulario] = useState<Record<Campo, string>>({
    limite_usuario_dia: '', limite_global_dia: '',
    limite_entrevista: '', retencao_dias: ''
  })
  const [carregando, setCarregando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    if (!aberto) return
    let ativo = true
    setCarregando(true)
    setErro('')
    apiGet<Configuracao>('/analise/admin/configuracoes')
      .then((resultado) => {
        if (!ativo) return
        setDados(resultado)
        setFormulario({
          limite_usuario_dia: String(resultado.limite_usuario_dia),
          limite_global_dia: String(resultado.limite_global_dia),
          limite_entrevista: String(resultado.limite_entrevista),
          retencao_dias: String(resultado.retencao_dias)
        })
      })
      .catch((falha: unknown) => {
        if (ativo) setErro(mensagem(falha))
      })
      .finally(() => {
        if (ativo) setCarregando(false)
      })
    return () => { ativo = false }
  }, [aberto])

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const valores = {
      limite_usuario_dia: Number(formulario.limite_usuario_dia),
      limite_global_dia: Number(formulario.limite_global_dia),
      limite_entrevista: Number(formulario.limite_entrevista),
      retencao_dias: Number(formulario.retencao_dias)
    }
    for (const campo of campos) {
      const valor = valores[campo.nome]
      if (!Number.isInteger(valor) || valor < campo.minimo || valor > campo.maximo) {
        setErro(`${campo.titulo}: informe um inteiro de ${campo.minimo} a ${campo.maximo}.`)
        return
      }
    }
    if (valores.limite_usuario_dia > valores.limite_global_dia) {
      setErro('O limite individual não pode ultrapassar o limite global diário.')
      return
    }
    setSalvando(true)
    setErro('')
    setAviso('')
    try {
      const atualizado = await apiPut<Configuracao, typeof valores>('/analise/admin/configuracoes', valores)
      setDados(atualizado)
      setAviso('Parâmetros atualizados e salvos no banco. Os contadores existentes foram preservados.')
      aoSalvar()
    } catch (falha: unknown) {
      setErro(mensagem(falha))
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div style={{ marginTop: 16 }}>
      <button type="button" className="button button--outline" onClick={() => { setAberto((valor) => !valor); setAviso('') }}>
        {aberto ? 'Fechar configurações' : 'Configurar parâmetros da IA'}
      </button>

      {aberto && (
        <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
          <h3>Limites e retenção de chamadas</h3>
          <p className="note">
            Somente administradores podem alterar estes valores.
            As alterações valem para novas reservas e não zeram as chamadas já consumidas.
          </p>
          {carregando && <p className="note">Carregando configurações...</p>}

          {dados && !carregando && (
            <form onSubmit={(evento) => void salvar(evento)}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,180px),1fr))', gap: 12 }}>
                {campos.map((campo) => (
                  <label key={campo.nome} className="field">
                    {campo.titulo}
                    <input type="number" required step="1" min={campo.minimo} max={campo.maximo}
                      value={formulario[campo.nome]} disabled={salvando}
                      onChange={(evento) => setFormulario((atual) => ({ ...atual, [campo.nome]: evento.target.value }))} />
                    <small className="note">{campo.explicacao}</small>
                  </label>
                ))}
              </div>
              <p className="note">
                Origem: {dados.personalizada ? 'Personalizada no banco SQLite' : 'Valores padrão do ambiente (.env)'}.
                {dados.alterado_em_utc ? ` Última alteração: ${dados.alterado_em_utc}.` : ''}
              </p>
              <p className="note">
                Atenção: reduzir uma cota abaixo do consumo atual bloqueia novas chamadas até haver saldo.
                Aumentar uma cota pode elevar os custos da OpenAI.
              </p>
              {erro && <p className="alert alert--error" role="alert">{erro}</p>}
              {aviso && <p className="note" role="status">{aviso}</p>}
              <button type="submit" className="button button--primary" disabled={salvando}>
                {salvando ? 'Salvando...' : 'Salvar parâmetros da IA'}
              </button>
            </form>
          )}
          {erro && (!dados || carregando) && <p className="alert alert--error" role="alert">{erro}</p>}
        </div>
      )}
    </div>
  )
}
