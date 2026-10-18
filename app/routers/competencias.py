
"""Rotas usadas para consultar e administrar as competências do simulador."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..competencias import (
    ativar_competencia,
    buscar_competencia,
    cadastrar_competencia,
    editar_competencia,
    inativar_competencia,
    listar_competencias,
    obter_detalhes_competencia
)
from ..models import Usuario
from ..schemas import CompetenciaAtualizar, CompetenciaCriar, CompetenciaDetalheResposta, CompetenciaResposta
from ..security import obter_administrador_atual, obter_usuario_atual

# Agrupa as rotas relacionadas às competências.
router = APIRouter(prefix="/competencias", tags=["Competências"])


@router.get("", response_model=list[CompetenciaResposta])
def listar(somente_ativas: bool = False, usuario: Usuario = Depends(obter_usuario_atual)):
    """Lista as competências para qualquer usuário autenticado."""
    # Estudantes não podem ampliar a consulta para competências inativas.
    if usuario.perfil != "administrador":
        somente_ativas = True
    return listar_competencias(somente_ativas=somente_ativas)


@router.get("/{competencia_id}", response_model=CompetenciaResposta)
def consultar(competencia_id: int, usuario: Usuario = Depends(obter_usuario_atual)):
    """Consulta uma competência pelo ID informado."""
    try:
        competencia = buscar_competencia(competencia_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    if competencia is None or (usuario.perfil != "administrador" and not competencia["ativo"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competência não encontrada.")

    return competencia


@router.get("/{competencia_id}/detalhes", response_model=CompetenciaDetalheResposta)
def consultar_detalhes(competencia_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Mostra informações administrativas sobre o uso de uma competência."""
    try:
        competencia = obter_detalhes_competencia(competencia_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    if competencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competência não encontrada.")

    return competencia


@router.post("", response_model=CompetenciaResposta, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: CompetenciaCriar, administrador: Usuario = Depends(obter_administrador_atual)):
    """Cadastra uma nova competência quando o usuário é administrador."""
    try:
        # Cria a competência e depois busca o registro para devolver os dados completos.
        competencia_id = cadastrar_competencia(nome=dados.nome, descricao=dados.descricao)
        competencia = buscar_competencia(competencia_id)

        if competencia is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A competência foi cadastrada, mas não pôde ser recuperada."
            )

        return competencia
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{competencia_id}", response_model=CompetenciaResposta)
def atualizar(
    competencia_id: int,
    dados: CompetenciaAtualizar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Atualiza o nome e a descrição da competência sem mudar seu status."""
    try:
        # Confirma a existência antes de tentar editar o registro.
        competencia = buscar_competencia(competencia_id)

        if competencia is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competência não encontrada.")

        alterada = editar_competencia(
            competencia_id=competencia_id,
            nome=dados.nome,
            descricao=dados.descricao
        )

        if not alterada:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competência não encontrada.")

        return buscar_competencia(competencia_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{competencia_id}/inativar", response_model=CompetenciaResposta)
def inativar(competencia_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Inativa uma competência sem excluir o registro ou seu histórico."""
    try:
        competencia = buscar_competencia(competencia_id)

        if competencia is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competência não encontrada.")

        alterada = inativar_competencia(competencia_id)

        if not alterada:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível inativar a competência.")

        return buscar_competencia(competencia_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{competencia_id}/ativar", response_model=CompetenciaResposta)
def ativar(competencia_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Reativa uma competência que estava inativa."""
    try:
        competencia = buscar_competencia(competencia_id)

        if competencia is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competência não encontrada.")

        alterada = ativar_competencia(competencia_id)

        if not alterada:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível ativar a competência.")

        return buscar_competencia(competencia_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
