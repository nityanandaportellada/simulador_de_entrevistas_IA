
import { useEffect, useState, type FormEvent } from 'react'
import { Loading } from '../../components/Loading'
import { AdminEntrevistasLista } from '../../components/AdminEntrevistasLista'
import { adminService } from '../../services/adminService'
import type { Competencia, CriterioAvaliacao, CriterioAvaliacaoRequest, TipoEntrevista } from '../../types/catalogos'

type Mode = 'tipos' | 'competencias' | 'criterios'
type CatalogoItem = TipoEntrevista | Competencia | CriterioAvaliacao
type Coluna = 'id' | 'nome' | 'area' | 'descricao' | 'peso' | 'ordem' | 'ativo' | 'acoes'
const vazio = { nome: '', descricao: '', peso: '0.10', ordem: '' }
const comparar = new Intl.Collator('pt-BR', { sensitivity: 'base', numeric: true })
const margem = 0.000000001

function mensagem(erro: unknown) {
  return erro instanceof Error ? erro.message : 'Não foi possível concluir a operação.'
}

export function CatalogoAdminPage({ mode }: { mode: Mode }) {
  const [items, setItems] = useState<CatalogoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [editando, setEditando] = useState<CatalogoItem | null>(null)
  const [aberto, setAberto] = useState(false)
  const [formulario, setFormulario] = useState(vazio)
  const [salvando, setSalvando] = useState(false)
  const [alterandoId, setAlterandoId] = useState<number | null>(null)
  const [erro, setErro] = useState('')
  const [ordenacao, setOrdenacao] = useState<{ coluna: Coluna; direcao: 'asc' | 'desc' }>({ coluna: 'id', direcao: 'asc' })

  async function carregar() {
    setLoading(true)
    try {
      if (mode === 'tipos') setItems(await adminService.tipos())
      if (mode === 'competencias') setItems(await adminService.competencias())
      if (mode === 'criterios') setItems(await adminService.criterios())
    } catch (falha: unknown) {
      setErro(mensagem(falha))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let ativo = true
    setAberto(false)
    setEditando(null)
    setErro('')
    setOrdenacao({ coluna: 'id', direcao: 'asc' })
    setLoading(true)
    const pedido = mode === 'tipos' ? adminService.tipos() : mode === 'competencias' ? adminService.competencias() : adminService.criterios()
    pedido.then((dados) => { if (ativo) setItems(dados) })
      .catch((falha: unknown) => { if (ativo) setErro(mensagem(falha)) })
      .finally(() => { if (ativo) setLoading(false) })
    return () => { ativo = false }
  }, [mode])

  const criterios = mode === 'criterios' ? items as CriterioAvaliacao[] : []
  const somaPesos = criterios.filter((item) => item.ativo).reduce((soma, item) => soma + item.peso, 0)
  const pesoAnterior = mode === 'criterios' && editando && 'peso' in editando && editando.ativo ? editando.peso : 0
  const pesoNovo = Number(formulario.peso.replace(',', '.'))
  const somaPrevista = somaPesos - pesoAnterior + (editando && !editando.ativo ? 0 : pesoNovo)
  const excede = mode === 'criterios' && Number.isFinite(pesoNovo) && somaPrevista > 1 + margem
  const titulo = mode === 'tipos' ? 'Entrevistas' : mode === 'competencias' ? 'Competências' : 'Critérios de avaliação'
  const colunas: { id: Coluna; titulo: string }[] = [
    { id: 'id', titulo: 'ID' }, { id: 'nome', titulo: 'Nome' },
    ...(mode === 'tipos' ? [{ id: 'area' as Coluna, titulo: 'Usa área técnica' }] : [{ id: 'descricao' as Coluna, titulo: 'Descrição' }]),
    ...(mode === 'criterios' ? [{ id: 'peso' as Coluna, titulo: 'Peso' }, { id: 'ordem' as Coluna, titulo: 'Ordem' }] : []),
    { id: 'ativo', titulo: 'Ativo' }, { id: 'acoes', titulo: 'Ações' }
  ]

  function valor(item: CatalogoItem, coluna: Coluna): string | number | null {
    if (coluna === 'id') return item.id
    if (coluna === 'nome') return item.nome
    if (coluna === 'area') return 'usa_area_tecnica' in item && item.usa_area_tecnica ? 1 : 0
    if (coluna === 'descricao') return 'descricao' in item ? item.descricao : null
    if (coluna === 'peso') return 'peso' in item ? item.peso : null
    if (coluna === 'ordem') return 'ordem' in item ? item.ordem : null
    if (coluna === 'ativo') return item.ativo ? 1 : 0
    return item.ativo ? 'Inativar' : 'Ativar'
  }

  const ordenados = [...items].sort((a, b) => {
    const x = valor(a, ordenacao.coluna)
    const y = valor(b, ordenacao.coluna)
    if (x == null && y == null) return a.id - b.id
    if (x == null) return 1
    if (y == null) return -1
    const resultado = typeof x === 'number' && typeof y === 'number' ? x - y : comparar.compare(String(x), String(y))
    return resultado === 0 ? a.id - b.id : resultado * (ordenacao.direcao === 'asc' ? 1 : -1)
  })

  function ordenar(coluna: Coluna) {
    setOrdenacao((atual) => ({ coluna, direcao: atual.coluna === coluna && atual.direcao === 'asc' ? 'desc' : 'asc' }))
  }

  function abrir(item?: CatalogoItem) {
    setEditando(item ?? null)
    setFormulario({
      nome: item?.nome ?? '', descricao: item && 'descricao' in item ? item.descricao ?? '' : '',
      peso: item && 'peso' in item ? String(item.peso) : '0.10',
      ordem: item && 'ordem' in item && item.ordem != null ? String(item.ordem) : ''
    })
    setErro('')
    setAberto(true)
  }

  async function alternar(item: CatalogoItem) {
    if (alterandoId !== null || salvando) return
    if (mode === 'criterios' && !item.ativo && 'peso' in item && somaPesos + item.peso > 1 + margem) {
      setErro('Não é possível ativar: a soma dos pesos ativos ultrapassaria 1,00.')
      return
    }
    setAlterandoId(item.id)
    setErro('')
    try {
      if (mode === 'tipos') {
        if (item.ativo) await adminService.inativarTipo(item.id)
        else await adminService.ativarTipo(item.id)
      } else if (mode === 'competencias') {
        if (item.ativo) await adminService.inativarCompetencia(item.id)
        else await adminService.ativarCompetencia(item.id)
      } else {
        if (item.ativo) await adminService.inativarCriterio(item.id)
        else await adminService.ativarCriterio(item.id)
      }
      await carregar()
    } catch (falha: unknown) {
      setErro(mensagem(falha))
    } finally {
      setAlterandoId(null)
    }
  }

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const nome = formulario.nome.trim()
    if (nome.length < 2 || nome.length > 150) { setErro('O nome deve conter de 2 a 150 caracteres.'); return }
    if (mode === 'criterios') {
      const ordem = formulario.ordem.trim() ? Number(formulario.ordem) : null
      if (!Number.isFinite(pesoNovo) || pesoNovo <= 0 || (ordem !== null && (!Number.isInteger(ordem) || ordem <= 0))) {
        setErro('Informe um peso maior que zero e, se preenchida, uma ordem inteira positiva.'); return
      }
      if (excede) { setErro('A soma dos pesos dos critérios ativos não pode ultrapassar 1,00.'); return }
    }
    setSalvando(true)
    setErro('')
    try {
      if (mode === 'tipos') {
        if (editando) await adminService.editarTipo(editando.id, { nome })
        else await adminService.criarTipo({ nome })
      } else if (mode === 'competencias') {
        const dados = { nome, descricao: formulario.descricao.trim() || null }
        if (editando) await adminService.editarCompetencia(editando.id, dados)
        else await adminService.criarCompetencia(dados)
      } else {
        const dados: CriterioAvaliacaoRequest = { nome, descricao: formulario.descricao.trim() || null, peso: pesoNovo, ordem: formulario.ordem.trim() ? Number(formulario.ordem) : null }
        if (editando) await adminService.editarCriterio(editando.id, dados)
        else await adminService.criarCriterio(dados)
      }
      setAberto(false)
      setEditando(null)
      await carregar()
    } catch (falha: unknown) {
      setErro(mensagem(falha))
    } finally {
      setSalvando(false)
    }
  }

  if (loading && items.length === 0 && !erro) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div><h1>{titulo}</h1><p>Cadastre, edite, classifique e ative ou inative registros.</p></div>
        <button type="button" className="button button--primary" disabled={loading || alterandoId !== null} onClick={() => abrir()}>
          Novo {mode === 'tipos' ? 'tipo' : mode === 'competencias' ? 'competência' : 'critério'}
        </button>
      </div>
      {erro && !aberto && <p role="alert" className="alert alert--error">{erro}</p>}
      {mode === 'criterios' && <p className="note">Soma dos pesos ativos: <strong>{somaPesos.toFixed(2).replace('.', ',')}</strong> / 1,00.</p>}
      <section className="panel">
        {mode === 'tipos' && <div className="panel__heading"><h2>Tipos de entrevista</h2><p>Cadastre e gerencie as modalidades disponíveis.</p></div>}
        <p className="note">Clique no cabeçalho de uma coluna para alternar entre ordem crescente e decrescente.</p>
        <div className="table-wrap"><table>
          <thead><tr>{colunas.map((coluna) => {
            const ativa = ordenacao.coluna === coluna.id
            return <th key={coluna.id} scope="col" aria-sort={ativa ? ordenacao.direcao === 'asc' ? 'ascending' : 'descending' : 'none'}>
              <button type="button" onClick={() => ordenar(coluna.id)} title={`Ordenar por ${coluna.titulo}`} style={{ border: 0, background: 'transparent', color: 'inherit', cursor: 'pointer', font: 'inherit', fontWeight: 'inherit', textTransform: 'inherit', whiteSpace: 'nowrap', padding: 0 }}>
                {coluna.titulo} {ativa ? ordenacao.direcao === 'asc' ? '↑' : '↓' : '↕'}
              </button>
            </th>
          })}</tr></thead>
          <tbody>{ordenados.map((item) => <tr key={item.id}>
            <td>{item.id}</td><td>{item.nome}</td>
            {mode === 'tipos' && <td>{'usa_area_tecnica' in item && item.usa_area_tecnica ? 'Sim' : 'Não'}</td>}
            {mode !== 'tipos' && <td>{'descricao' in item ? item.descricao ?? '-' : '-'}</td>}
            {mode === 'criterios' && <><td>{'peso' in item ? item.peso.toFixed(2).replace('.', ',') : '-'}</td><td>{'ordem' in item ? item.ordem ?? '-' : '-'}</td></>}
            <td>{item.ativo ? 'Sim' : 'Não'}</td><td><div className="button-row">
              <button type="button" className="button button--small button--outline" disabled={loading || alterandoId !== null} onClick={() => abrir(item)}>Editar</button>
              <button type="button" className="button button--small button--outline" disabled={loading || alterandoId !== null} onClick={() => void alternar(item)}>{alterandoId === item.id ? 'Salvando...' : item.ativo ? 'Inativar' : 'Ativar'}</button>
            </div></td>
          </tr>)}
          {ordenados.length === 0 && <tr><td colSpan={colunas.length}>Nenhum registro encontrado.</td></tr>}
          </tbody>
        </table></div>
      </section>
      {mode === 'tipos' && <AdminEntrevistasLista modo ="completo" />}
      {aberto && <div role="presentation" style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(10,25,60,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
        <section role="dialog" aria-modal="true" aria-labelledby="titulo-catalogo" className="panel" style={{ width: '100%', maxWidth: 560, maxHeight: '90vh', overflowY: 'auto', background: 'white' }}>
          <h2 id="titulo-catalogo">{editando ? 'Editar' : 'Novo cadastro'} — {titulo}</h2>
          <form onSubmit={(evento) => void salvar(evento)} style={{ display: 'grid', gap: 16, marginTop: 20 }}>
            <label className="field">Nome<input required minLength={2} maxLength={150} value={formulario.nome} onChange={(evento) => setFormulario({ ...formulario, nome: evento.target.value })} /></label>
            {mode !== 'tipos' && <label className="field">Descrição<textarea maxLength={2000} rows={3} value={formulario.descricao} onChange={(evento) => setFormulario({ ...formulario, descricao: evento.target.value })} /></label>}
            {mode === 'criterios' && <>
              <label className="field">Peso<input required type="number" min="0.000001" step="any" value={formulario.peso} onChange={(evento) => setFormulario({ ...formulario, peso: evento.target.value })} /></label>
              <label className="field">Ordem (opcional)<input type="number" min="1" step="1" value={formulario.ordem} onChange={(evento) => setFormulario({ ...formulario, ordem: evento.target.value })} /></label>
              <p className="note">Soma prevista de pesos ativos: {Number.isFinite(somaPrevista) ? somaPrevista.toFixed(2).replace('.', ',') : '-'} / 1,00. {editando && !editando.ativo ? 'O critério está inativo; seu peso só entra na soma ao ser ativado.' : ''}</p>
              {excede && <p className="alert alert--error" role="alert">A soma ultrapassaria 1,00.</p>}
            </>}
            {erro && <p className="alert alert--error" role="alert">{erro}</p>}
            <div className="button-row button-row--end">
              <button type="button" className="button button--ghost" disabled={salvando} onClick={() => { setAberto(false); setErro('') }}>Cancelar</button>
              <button type="submit" className="button button--primary" disabled={salvando || excede}>{salvando ? 'Salvando...' : 'Salvar'}</button>
            </div>
          </form>
        </section>
      </div>}
    </div>
  )
}
