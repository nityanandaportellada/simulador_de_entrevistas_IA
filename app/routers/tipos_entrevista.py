"""Rotas usadas para consultar e administrar os tipos de entrevista."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import Usuario
from ..schemas import TipoEntrevistaAtualizar, TipoEntrevistaCriar, TipoEntrevistaDetalheResposta, TipoEntrevistaResposta
from ..security import obter_administrador_atual, obter_usuario_atual
from ..tipos_entrevista import (
    ativar_tipo_entrevista,
    buscar_tipo_entrevista,
    cadastrar_tipo_entrevista,
    editar_tipo_entrevista,
    inativar_tipo_entrevista,
    listar_tipos_entrevista,
    obter_detalhes_tipo_entrevista
)

# Agrupa as rotas relacionadas aos tipos de entrevista.
router = APIRouter(prefix="/tipos-entrevista", tags=["Tipos de Entrevista"])


@router.get("", response_model=list[TipoEntrevistaResposta])
def listar(somente_ativos: bool = False, usuario: Usuario = Depends(obter_usuario_atual)):
    """Lista os tipos de entrevista para qualquer usuário autenticado."""
    # O parâmetro permite que a interface peça somente os tipos disponíveis.
    return listar_tipos_entrevista(somente_ativos=somente_ativos)


@router.get("/{tipo_entrevista_id}", response_model=TipoEntrevistaResposta)
def consultar(tipo_entrevista_id: int, usuario: Usuario = Depends(obter_usuario_atual)):
    """Consulta um tipo de entrevista pelo ID informado."""
    try:
        tipo = buscar_tipo_entrevista(tipo_entrevista_id)
    except ValueError as erro:
        # Erros de validação do serviço são devolvidos como requisição inválida.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    if tipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de entrevista não encontrado.")

    return tipo


@router.get("/{tipo_entrevista_id}/detalhes", response_model=TipoEntrevistaDetalheResposta)
def consultar_detalhes(tipo_entrevista_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Mostra informações administrativas sobre o uso de um tipo de entrevista."""
    try:
        tipo = obter_detalhes_tipo_entrevista(tipo_entrevista_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    if tipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de entrevista não encontrado.")

    return tipo


@router.post("", response_model=TipoEntrevistaResposta, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: TipoEntrevistaCriar, administrador: Usuario = Depends(obter_administrador_atual)):
    """Cadastra um novo tipo de entrevista quando o usuário é administrador."""
    try:
        # Primeiro cria o registro e depois o busca para devolver o objeto completo.
        tipo_entrevista_id = cadastrar_tipo_entrevista(dados.nome)
        tipo_criado = buscar_tipo_entrevista(tipo_entrevista_id)

        if tipo_criado is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="O tipo de entrevista foi cadastrado, mas não pôde ser recuperado."
            )

        return tipo_criado
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{tipo_entrevista_id}", response_model=TipoEntrevistaResposta)
def atualizar(
    tipo_entrevista_id: int,
    dados: TipoEntrevistaAtualizar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Atualiza o nome do tipo de entrevista sem alterar seu status."""
    try:
        # Confirma a existência antes de tentar fazer a alteração.
        tipo_atual = buscar_tipo_entrevista(tipo_entrevista_id)

        if tipo_atual is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de entrevista não encontrado.")

        alterado = editar_tipo_entrevista(tipo_entrevista_id, dados.nome)

        if not alterado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de entrevista não encontrado.")

        return buscar_tipo_entrevista(tipo_entrevista_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{tipo_entrevista_id}/inativar", response_model=TipoEntrevistaResposta)
def inativar(tipo_entrevista_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Inativa um tipo de entrevista sem apagar o registro e o histórico relacionado."""
    try:
        tipo = buscar_tipo_entrevista(tipo_entrevista_id)

        if tipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de entrevista não encontrado.")

        alterado = inativar_tipo_entrevista(tipo_entrevista_id)

        if not alterado:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível inativar o tipo de entrevista.")

        return buscar_tipo_entrevista(tipo_entrevista_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{tipo_entrevista_id}/ativar", response_model=TipoEntrevistaResposta)
def ativar(tipo_entrevista_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Reativa um tipo de entrevista que estava inativo."""
    try:
        tipo = buscar_tipo_entrevista(tipo_entrevista_id)

        if tipo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de entrevista não encontrado.")

        alterado = ativar_tipo_entrevista(tipo_entrevista_id)

        if not alterado:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível ativar o tipo de entrevista.")

        return buscar_tipo_entrevista(tipo_entrevista_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))