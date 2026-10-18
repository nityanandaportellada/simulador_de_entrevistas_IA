
"""Rotas usadas para iniciar, responder, consultar e finalizar entrevistas."""

from dataclasses import asdict
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ..entrevistas import (
    buscar_entrevista,
    contar_perguntas_entrevista,
    criar_entrevista,
    finalizar_entrevista,
    listar_perguntas_entrevista
)
from ..models import Usuario
from ..respostas import contar_respostas_entrevista, listar_respostas_entrevista, salvar_resposta
from ..schemas import RespostaCriar
from ..security import obter_usuario_atual


class EntrevistaCriar(BaseModel):
    """Dados aceitos para iniciar uma entrevista."""

    # Campos extras são rejeitados. O usuario_id sempre vem do token JWT.
    model_config = ConfigDict(extra="forbid")

    tipo_entrevista_id: int = Field(gt=0)
    area_tecnica_id: Optional[int] = Field(default=None, gt=0)
    subarea_tecnica_id: Optional[int] = Field(default=None, gt=0)
    # O perfil define a quantidade de perguntas por dificuldade.
    perfil_profissional: Literal["estagio_trainee", "junior", "pleno", "senior"]


# Agrupa as rotas relacionadas às entrevistas.
router = APIRouter(prefix="/entrevistas", tags=["Entrevistas"])


def _obter_entrevista_autorizada(entrevista_id: int, usuario: Usuario, exigir_proprietario: bool = False):
    """Permite leitura administrativa, mas exige proprietário nas alterações."""
    if entrevista_id <= 0:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada.")
    entrevista = buscar_entrevista(entrevista_id)

    if entrevista is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrevista não encontrada."
        )

    # Para terceiros, 404 não revela se a entrevista existe.
    if entrevista.usuario_id != usuario.id and (exigir_proprietario or usuario.perfil != "administrador"):
        raise HTTPException(status_code=404, detail="Entrevista não encontrada.")

    return entrevista


def _ocultar_referencias(registros):
    """Entrega perguntas e respostas sem divulgar o gabarito guardado para a IA."""
    resultado = []
    for registro in registros:
        dados = asdict(registro)
        dados["exemplo_esperado_aplicado"] = None
        resultado.append(dados)
    return resultado


@router.post("", status_code=status.HTTP_201_CREATED)
def iniciar(
    dados: EntrevistaCriar,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Inicia uma entrevista para o usuário identificado pelo token."""
    if usuario.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário autenticado inválido."
        )

    try:
        # Área e subárea podem ser nulas ou obrigatórias conforme o tipo configurado no banco.
        entrevista_id = criar_entrevista(
            usuario_id=usuario.id,
            tipo_entrevista_id=dados.tipo_entrevista_id,
            area_tecnica_id=dados.area_tecnica_id,
            subarea_tecnica_id=dados.subarea_tecnica_id,
            perfil_profissional=dados.perfil_profissional
        )
        entrevista = buscar_entrevista(entrevista_id)

        if entrevista is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A entrevista foi criada, mas não pôde ser recuperada."
            )

        return entrevista

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.get("/{entrevista_id}")
def consultar(
    entrevista_id: int,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Consulta uma entrevista depois de verificar a autorização do usuário."""
    return _obter_entrevista_autorizada(entrevista_id, usuario)


@router.get("/{entrevista_id}/perguntas")
def perguntas(
    entrevista_id: int,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Retorna as perguntas congeladas, sem revelar as respostas de referência."""
    _obter_entrevista_autorizada(entrevista_id, usuario)

    try:
        return _ocultar_referencias(listar_perguntas_entrevista(entrevista_id))
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.post("/{entrevista_id}/respostas", status_code=status.HTTP_201_CREATED)
def responder(
    entrevista_id: int,
    dados: RespostaCriar,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Registra uma resposta para uma pergunta pertencente à entrevista."""
    entrevista = _obter_entrevista_autorizada(entrevista_id, usuario, exigir_proprietario=True)

    if entrevista.status != "em_andamento":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível responder uma entrevista que não está em andamento."
        )

    try:
        # O serviço confirma se a pergunta faz parte do conjunto congelado.
        resposta_id = salvar_resposta(
            entrevista_id=entrevista_id,
            pergunta_id=dados.pergunta_id,
            texto_resposta=dados.texto_resposta,
            tempo_resposta=dados.tempo_resposta
        )

        return {
            "id": resposta_id,
            "entrevista_id": entrevista_id,
            "pergunta_id": dados.pergunta_id,
            "mensagem": "Resposta registrada com sucesso."
        }

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.get("/{entrevista_id}/respostas")
def respostas(
    entrevista_id: int,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Lista as respostas registradas sem revelar os exemplos usados na avaliação."""
    _obter_entrevista_autorizada(entrevista_id, usuario)
    return _ocultar_referencias(listar_respostas_entrevista(entrevista_id))


@router.get("/{entrevista_id}/progresso")
def progresso(
    entrevista_id: int,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Mostra quantas perguntas já foram respondidas e quantas ainda estão pendentes."""
    _obter_entrevista_autorizada(entrevista_id, usuario)
    quantidade_perguntas = contar_perguntas_entrevista(entrevista_id)
    quantidade_respostas = contar_respostas_entrevista(entrevista_id)

    return {
        "entrevista_id": entrevista_id,
        "quantidade_perguntas": quantidade_perguntas,
        "quantidade_respostas": quantidade_respostas,
        "quantidade_pendentes": max(0, quantidade_perguntas - quantidade_respostas),
        "todas_respondidas": quantidade_perguntas > 0 and quantidade_respostas >= quantidade_perguntas
    }


@router.post("/{entrevista_id}/finalizar")
def finalizar(
    entrevista_id: int,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Finaliza a entrevista; o serviço confirma que todas as perguntas foram respondidas."""
    entrevista = _obter_entrevista_autorizada(entrevista_id, usuario, exigir_proprietario=True)

    if entrevista.status != "em_andamento":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A entrevista não está em andamento."
        )

    quantidade_perguntas = contar_perguntas_entrevista(entrevista_id)

    if quantidade_perguntas <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A entrevista não possui perguntas congeladas e não pode ser finalizada."
        )

    respostas_registradas = listar_respostas_entrevista(entrevista_id)

    if not respostas_registradas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A entrevista não pode ser finalizada sem respostas."
        )

    try:
        # A validação definitiva de todas as respostas acontece dentro da transação do serviço.
        resultado = finalizar_entrevista(entrevista_id)

        if not resultado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível finalizar a entrevista."
            )

        entrevista_finalizada = buscar_entrevista(entrevista_id)

        if entrevista_finalizada is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A entrevista foi finalizada, mas não pôde ser recuperada."
            )

        return {
            "entrevista_id": entrevista_id,
            "status": entrevista_finalizada.status,
            "data_fim": entrevista_finalizada.data_fim,
            "quantidade_perguntas": quantidade_perguntas,
            "quantidade_respostas": len(respostas_registradas),
            "mensagem": "Entrevista finalizada com sucesso."
        }

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )
