
import { useEffect, useState, type FormEvent } from 'react'
import { Loading } from '../../components/Loading'
import { adminService } from '../../services/adminService'
import type { AreaTecnica, Competencia, SubareaTecnica, TipoEntrevista } from '../../types/catalogos'
import type { DificuldadePergunta, Pergunta, PerguntaRequest } from '../../types/pergunta'

type Formulario = {
  tipo: string; competencia: string; area: string; subarea: string; texto: string
  referencia: string; codigo: string; dificuldade: DificuldadePergunta | ''
  ordem: string; peso: string; usaStar: boolean
}
type ColunaOrdenacao = 'id' | 'codigo' | 'texto' | 'tipo' | 'dificuldade' | 'competencia' | 'contexto' | 'peso' | 'star' | 'status' | 'acoes'
type DirecaoOrdenacao = 'asc' | 'desc'

const vazio: Formulario = {
  tipo: '', competencia: '', area: '', subarea: '', texto: '', referencia: '',
  codigo: '', dificuldade: '', ordem: '', peso: '1', usaStar: false
}
const COLUNAS: { campo: ColunaOrdenacao; titulo: string }[] = [
  { campo: 'id', titulo: 'ID' }, { campo: 'codigo', titulo: 'Código' },
  { campo: 'texto', titulo: 'Pergunta' }, { campo: 'tipo', titulo: 'Tipo' },
  { campo: 'dificuldade', titulo: 'Dificuldade' }, { campo: 'competencia', titulo: 'Competência' },
  { campo: 'contexto', titulo: 'Contexto técnico' }, { campo: 'peso', titulo: 'Peso' },
  { campo: 'star', titulo: 'STAR' }, { campo: 'status', titulo: 'Status' },
  { campo: 'acoes', titulo: 'Ações' }
]
const ORDEM_DIFICULDADES: Record<DificuldadePergunta, number> = { basica: 1, intermediaria: 2, avancada: 3 }
const comparadorTexto = new Intl.Collator('pt-BR', { sensitivity: 'base', numeric: true })

function mensagemErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : 'Não foi possível concluir a operação.'
}

export function PerguntasAdminPage() {
  const [items, setItems] = useState<Pergunta[]>([])
  const [tipos, setTipos] = useState<TipoEntrevista[]>([])
  const [competencias, setCompetencias] = useState<Competencia[]>([])
  const [areas, setAreas] = useState<AreaTecnica[]>([])
  const [subareas, setSubareas] = useState<SubareaTecnica[]>([])
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [alterandoId, setAlterandoId] = useState<number | null>(null)
  const [editando, setEditando] = useState<Pergunta | null>(null)
  const [formularioAberto, setFormularioAberto] = useState(false)
  const [formulario, setFormulario] = useState<Formulario>(vazio)
  const [erro, setErro] = useState('')
  const [busca, setBusca] = useState('')
  const [filtroTipo, setFiltroTipo] = useState('')
  const [ordenacao, setOrdenacao] = useState<{ campo: ColunaOrdenacao; direcao: DirecaoOrdenacao } | null>(null)

  async function carregar() {
    setLoading(true)
    try {
      const [perguntas, tiposRecebidos, competenciasRecebidas, areasRecebidas, subareasRecebidas] = await Promise.all([
        adminService.perguntas(), adminService.tipos(), adminService.competencias(), adminService.areas(), adminService.subareas()
      ])
      setItems(perguntas)
      setTipos(tiposRecebidos)
      setCompetencias(competenciasRecebidas)
      setAreas(areasRecebidas)
      setSubareas(subareasRecebidas)
      setErro('')
    } catch (falha: unknown) {
      setErro(mensagemErro(falha))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void carregar() }, [])

  const tipoAtual = tipos.find((tipo) => tipo.id === Number(formulario.tipo))
  const tecnica = Boolean(tipoAtual?.usa_area_tecnica)
  const subareasDaArea = subareas.filter((subarea) => subarea.area_tecnica_id === Number(formulario.area) && subarea.ativo)

  function nomeTipo(id: number): string {
    return tipos.find((tipo) => tipo.id === id)?.nome ?? `#${id}`
  }

  function nomeCompetencia(id: number | null): string {
    if (id === null) return '-'
    return competencias.find((competencia) => competencia.id === id)?.nome ?? `#${id}`
  }

  function contextoTecnico(item: Pergunta): string {
    if (!item.area_tecnica_id) return '-'
    const area = areas.find((registro) => registro.id === item.area_tecnica_id)?.nome ?? `Área #${item.area_tecnica_id}`
    if (!item.subarea_tecnica_id) return area
    const subarea = subareas.find((registro) => registro.id === item.subarea_tecnica_id)?.nome ?? `Subárea #${item.subarea_tecnica_id}`
    return `${area} / ${subarea}`
  }

  // As dificuldades seguem a progressão pedagógica, e não a ordem alfabética.
  function valorOrdenacao(item: Pergunta, campo: ColunaOrdenacao): string | number | null {
    if (campo === 'id') return item.id
    if (campo === 'codigo') return item.codigo?.trim() || null
    if (campo === 'texto') return item.texto
    if (campo === 'tipo') return nomeTipo(item.tipo_entrevista_id)
    if (campo === 'dificuldade') return item.dificuldade ? ORDEM_DIFICULDADES[item.dificuldade] : null
    if (campo === 'competencia') return item.competencia_id === null ? null : nomeCompetencia(item.competencia_id)
    if (campo === 'contexto') return item.area_tecnica_id === null ? null : contextoTecnico(item)
    if (campo === 'peso') return item.peso
    if (campo === 'star') return item.usa_star ? 1 : 0
    if (campo === 'status') return item.ativa ? 'Ativa' : 'Inativa'
    return item.ativa ? 'Inativar' : 'Ativar'
  }

  function ordenarPor(campo: ColunaOrdenacao) {
    setOrdenacao((anterior) => ({
      campo,
      direcao: anterior?.campo === campo && anterior.direcao === 'asc' ? 'desc' : 'asc'
    }))
  }

  // Os filtros são aplicados antes da ordenação; valores não preenchidos ficam ao final.
  const filtradas = items.filter((item) => {
    const termo = busca.trim().toLocaleLowerCase('pt-BR')
    const corresponde = !termo || String(item.id) === termo || (item.codigo ?? '').toLocaleLowerCase('pt-BR').includes(termo) || item.texto.toLocaleLowerCase('pt-BR').includes(termo)
    return corresponde && (!filtroTipo || item.tipo_entrevista_id === Number(filtroTipo))
  })
  if (ordenacao) {
    const campo = ordenacao.campo
    const fator = ordenacao.direcao === 'asc' ? 1 : -1
    filtradas.sort((a, b) => {
      const primeiro = valorOrdenacao(a, campo)
      const segundo = valorOrdenacao(b, campo)
      if (primeiro === null && segundo === null) return a.id - b.id
      if (primeiro === null) return 1
      if (segundo === null) return -1
      const comparacao = typeof primeiro === 'number' && typeof segundo === 'number'
        ? primeiro - segundo : comparadorTexto.compare(String(primeiro), String(segundo))
      return comparacao === 0 ? a.id - b.id : comparacao * fator
    })
  }

  function abrirFormulario(item?: Pergunta) {
    setEditando(item ?? null)
    setFormulario(item ? {
      tipo: String(item.tipo_entrevista_id), competencia: item.competencia_id == null ? '' : String(item.competencia_id),
      area: item.area_tecnica_id == null ? '' : String(item.area_tecnica_id),
      subarea: item.subarea_tecnica_id == null ? '' : String(item.subarea_tecnica_id),
      texto: item.texto, referencia: item.exemplo_esperado ?? '', codigo: item.codigo ?? '',
      dificuldade: item.dificuldade ?? '', ordem: item.ordem == null ? '' : String(item.ordem),
      peso: String(item.peso), usaStar: item.usa_star
    } : { ...vazio })
    setErro('')
    setFormularioAberto(true)
  }

  async function alternar(item: Pergunta) {
    if (alterandoId !== null || salvando) return
    setErro('')
    setAlterandoId(item.id)
    try {
      if (item.ativa) await adminService.inativarPergunta(item.id)
      else await adminService.ativarPergunta(item.id)
      await carregar()
    } catch (falha: unknown) {
      setErro(mensagemErro(falha))
    } finally {
      setAlterandoId(null)
    }
  }

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const tipoId = Number(formulario.tipo)
    const competenciaId = formulario.competencia ? Number(formulario.competencia) : null
    const areaId = formulario.area ? Number(formulario.area) : null
    const subareaId = formulario.subarea ? Number(formulario.subarea) : null
    const peso = Number(formulario.peso.replace(',', '.'))
    const ordem = formulario.ordem.trim() ? Number(formulario.ordem) : null
    const codigo = formulario.codigo.trim() || null
    const texto = formulario.texto.trim()
    const referencia = formulario.referencia.trim() || null
    const dificuldade = formulario.dificuldade || null

    if (!tipoAtual?.ativo) {
      setErro('Selecione um tipo de entrevista ativo.')
      return
    }
    if (texto.length < 3 || texto.length > 4000 || (referencia !== null && referencia.length > 8000)) {
      setErro('A pergunta deve ter de 3 a 4.000 caracteres; a referência pode ter até 8.000 caracteres.')
      return
    }
    if (!Number.isFinite(peso) || peso <= 0 || (ordem !== null && (!Number.isInteger(ordem) || ordem <= 0))) {
      setErro('Informe um peso positivo e uma ordem inteira maior que zero, quando preenchida.')
      return
    }
    if (codigo !== null && (codigo.length < 3 || codigo.length > 30)) {
      setErro('O código deve ter de 3 a 30 caracteres.')
      return
    }
    if (!editando && (!codigo || !dificuldade)) {
      setErro('Para uma nova pergunta, informe o código único e o nível de dificuldade.')
      return
    }
    if (!tecnica && (!competenciaId || !competencias.some((item) => item.id === competenciaId && item.ativo))) {
      setErro('Selecione uma competência ativa para este tipo de entrevista.')
      return
    }
    if (competenciaId !== null && !competencias.some((item) => item.id === competenciaId && item.ativo)) {
      setErro('A competência selecionada está inativa.')
      return
    }
    if (tecnica && (!areaId || !subareaId || !areas.some((item) => item.id === areaId && item.ativo) ||
      !subareas.some((item) => item.id === subareaId && item.area_tecnica_id === areaId && item.ativo))) {
      setErro('Selecione uma área ativa e uma subárea ativa pertencente a ela.')
      return
    }

    const dados: PerguntaRequest = {
      tipo_entrevista_id: tipoId, competencia_id: competenciaId, texto,
      exemplo_esperado: referencia, codigo, dificuldade, ordem,
      peso, usa_star: formulario.usaStar,
      area_tecnica_id: tecnica ? areaId : null, subarea_tecnica_id: tecnica ? subareaId : null
    }
    setSalvando(true)
    setErro('')
    try {
      if (editando) await adminService.editarPergunta(editando.id, dados)
      else await adminService.criarPergunta(dados)
      setFormularioAberto(false)
      setEditando(null)
      await carregar()
    } catch (falha: unknown) {
      setErro(mensagemErro(falha))
    } finally {
      setSalvando(false)
    }
  }

  if (loading && items.length === 0 && !erro) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div><h1>Gestão de perguntas</h1><p>Cadastre, edite e controle as perguntas usadas nas entrevistas.</p></div>
        <button type="button" className="button button--primary" disabled={loading || alterandoId !== null} onClick={() => abrirFormulario()}>Nova pergunta</button>
      </div>
      {erro && !formularioAberto && <p role="alert" style={{ color: '#b42318' }}>{erro}</p>}
      <section className="panel">
        <div className="two-column" style={{ marginBottom: 16 }}>
          <label className="field">Buscar por texto, código ou ID
            <input value={busca} onChange={(evento) => setBusca(evento.target.value)} placeholder="Buscar pergunta..." />
          </label>
          <label className="field">Filtrar por tipo
            <select value={filtroTipo} onChange={(evento) => setFiltroTipo(evento.target.value)}>
              <option value="">Todos os tipos</option>
              {tipos.map((tipo) => <option key={tipo.id} value={tipo.id}>{tipo.nome}</option>)}
            </select>
          </label>
        </div>
        <p className="note">Exibindo {filtradas.length} de {items.length} perguntas. Clique no título de qualquer coluna para classificar em ordem crescente ou decrescente. A resposta de referência é exibida apenas ao administrador.</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {COLUNAS.map(({ campo, titulo }) => {
                  const selecionada = ordenacao?.campo === campo
                  const proximaDirecao = selecionada && ordenacao.direcao === 'asc' ? 'decrescente' : 'crescente'
                  return (
                    <th key={campo} scope="col" aria-sort={selecionada ? ordenacao.direcao === 'asc' ? 'ascending' : 'descending' : 'none'}>
                      <button type="button" title={`Ordenar ${titulo.toLowerCase()} em ordem ${proximaDirecao}`}
                        aria-label={`Ordenar por ${titulo}, ordem ${proximaDirecao}`}
                        onClick={() => ordenarPor(campo)}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 5, background: 'transparent', border: 0, padding: 0, color: 'inherit', font: 'inherit', textTransform: 'inherit', fontWeight: 'inherit', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                        {titulo}<span aria-hidden="true" style={{ fontSize: '.9rem' }}>{selecionada ? ordenacao.direcao === 'asc' ? '↑' : '↓' : '↕'}</span>
                      </button>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {filtradas.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td><td>{item.codigo ?? '-'}</td><td className="table-text">{item.texto}</td>
                  <td>{nomeTipo(item.tipo_entrevista_id)}</td><td>{item.dificuldade ?? '-'}</td>
                  <td>{nomeCompetencia(item.competencia_id)}</td><td>{contextoTecnico(item)}</td>
                  <td>{item.peso}</td><td>{item.usa_star ? 'Sim' : 'Não'}</td><td>{item.ativa ? 'Ativa' : 'Inativa'}</td>
                  <td><div className="button-row">
                    <button type="button" className="button button--small button--outline" disabled={loading || alterandoId !== null} onClick={() => abrirFormulario(item)}>Editar</button>
                    <button type="button" className="button button--small button--outline" disabled={loading || alterandoId !== null} onClick={() => void alternar(item)}>{alterandoId === item.id ? 'Salvando...' : item.ativa ? 'Inativar' : 'Ativar'}</button>
                  </div></td>
                </tr>
              ))}
              {filtradas.length === 0 && <tr><td colSpan={COLUNAS.length}>Nenhuma pergunta encontrada.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
      {formularioAberto && (
        <div role="presentation" style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(10, 25, 60, .55)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
          <section role="dialog" aria-modal="true" aria-labelledby="titulo-formulario-pergunta" className="panel" style={{ width: '100%', maxWidth: 760, maxHeight: '92vh', overflowY: 'auto', background: 'white' }}>
            <h2 id="titulo-formulario-pergunta">{editando ? `Editar pergunta #${editando.id}` : 'Cadastrar pergunta'}</h2>
            <form onSubmit={(evento) => void salvar(evento)} style={{ display: 'grid', gap: 14, marginTop: 20 }}>
              <label className="field">Tipo de entrevista
                <select required value={formulario.tipo} onChange={(evento) => setFormulario({ ...formulario, tipo: evento.target.value, competencia: '', area: '', subarea: '' })}>
                  <option value="">Selecione o tipo</option>
                  {tipos.map((tipo) => <option key={tipo.id} value={tipo.id}>{tipo.nome}{!tipo.ativo ? ' (inativo)' : ''}</option>)}
                </select>
              </label>
              <label className="field">Competência {tecnica ? '(opcional)' : '(obrigatória)'}
                <select required={!tecnica} value={formulario.competencia} onChange={(evento) => setFormulario({ ...formulario, competencia: evento.target.value })}>
                  <option value="">{tecnica ? 'Sem competência' : 'Selecione a competência'}</option>
                  {competencias.map((competencia) => <option key={competencia.id} value={competencia.id}>{competencia.nome}{!competencia.ativo ? ' (inativa)' : ''}</option>)}
                </select>
              </label>
              {tecnica && (
                <div className="two-column">
                  <label className="field">Área técnica
                    <select required value={formulario.area} onChange={(evento) => setFormulario({ ...formulario, area: evento.target.value, subarea: '' })}>
                      <option value="">Selecione a área</option>
                      {areas.map((area) => <option key={area.id} value={area.id}>{area.nome}{!area.ativo ? ' (inativa)' : ''}</option>)}
                    </select>
                  </label>
                  <label className="field">Subárea técnica
                    <select required value={formulario.subarea} disabled={!formulario.area} onChange={(evento) => setFormulario({ ...formulario, subarea: evento.target.value })}>
                      <option value="">Selecione a subárea</option>
                      {subareasDaArea.map((subarea) => <option key={subarea.id} value={subarea.id}>{subarea.nome}</option>)}
                    </select>
                  </label>
                </div>
              )}
              <label className="field">Enunciado da pergunta
                <textarea required minLength={3} maxLength={4000} rows={4} value={formulario.texto} onChange={(evento) => setFormulario({ ...formulario, texto: evento.target.value })} />
              </label>
              <label className="field">Resposta de referência (visível somente à administração)
                <textarea maxLength={8000} rows={4} value={formulario.referencia} onChange={(evento) => setFormulario({ ...formulario, referencia: evento.target.value })} />
              </label>
              <div className="two-column">
                <label className="field">Código único
                  <input required={!editando} minLength={3} maxLength={30} value={formulario.codigo} onChange={(evento) => setFormulario({ ...formulario, codigo: evento.target.value })} placeholder="TEC-B01" />
                </label>
                <label className="field">Dificuldade
                  <select required={!editando} value={formulario.dificuldade} onChange={(evento) => setFormulario({ ...formulario, dificuldade: evento.target.value as Formulario['dificuldade'] })}>
                    <option value="">Selecione a dificuldade</option>
                    <option value="basica">Básica</option><option value="intermediaria">Intermediária</option><option value="avancada">Avançada</option>
                  </select>
                </label>
              </div>
              <div className="two-column">
                <label className="field">Peso da pergunta
                  <input required type="number" min="0.000001" step="any" value={formulario.peso} onChange={(evento) => setFormulario({ ...formulario, peso: evento.target.value })} />
                </label>
                <label className="field">Ordem (opcional)
                  <input type="number" min="1" step="1" value={formulario.ordem} onChange={(evento) => setFormulario({ ...formulario, ordem: evento.target.value })} />
                </label>
              </div>
              <label><input type="checkbox" checked={formulario.usaStar} onChange={(evento) => setFormulario({ ...formulario, usaStar: evento.target.checked })} /> Utilizar método STAR</label>
              <p className="note">Código e dificuldade são necessários para a seleção automática de novas entrevistas. O peso da pergunta é independente da soma dos pesos dos critérios de avaliação.</p>
              {erro && <p role="alert" style={{ color: '#b42318' }}>{erro}</p>}
              <div className="button-row button-row--end">
                <button type="button" className="button button--ghost" disabled={salvando} onClick={() => { setFormularioAberto(false); setErro('') }}>Cancelar</button>
                <button type="submit" className="button button--primary" disabled={salvando}>{salvando ? 'Salvando...' : 'Salvar pergunta'}</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}
