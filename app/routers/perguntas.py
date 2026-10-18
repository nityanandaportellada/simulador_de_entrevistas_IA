
"""Rotas usadas para consultar e administrar o banco de perguntas."""

from dataclasses import replace
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ..models import Pergunta, Usuario
from ..perguntas import (
    buscar_pergunta,
    buscar_pergunta_ativa,
    cadastrar_pergunta,
    desativar_pergunta,
    editar_pergunta,
    listar_perguntas,
    reativar_pergunta
)
from ..security import obter_administrador_atual, obter_usuario_atual


class PerguntaCriar(BaseModel):
    """Define os dados permitidos no cadastro de uma pergunta."""

    # Rejeita campos desconhecidos enviados na requisição.
    model_config = ConfigDict(extra="forbid")

    tipo_entrevista_id: int = Field(gt=0)
    competencia_id: Optional[int] = Field(default=None, gt=0)
    texto: str = Field(min_length=3, max_length=4000)
    exemplo_esperado: Optional[str] = Field(default=None, max_length=8000)
    ordem: Optional[int] = Field(default=None, gt=0)
    peso: float = Field(default=1.0, gt=0)
    usa_star: bool = False
    area_tecnica_id: Optional[int] = Field(default=None, gt=0)
    subarea_tecnica_id: Optional[int] = Field(default=None, gt=0)
    codigo: Optional[str] = Field(default=None, min_length=3, max_length=30)
    dificuldade: Optional[str] = Field(default=None, pattern="^(basica|intermediaria|avancada)$")


class PerguntaAtualizar(BaseModel):
    """Define os dados permitidos na atualização de uma pergunta."""

    model_config = ConfigDict(extra="forbid")

    tipo_entrevista_id: int = Field(gt=0)
    competencia_id: Optional[int] = Field(default=None, gt=0)
    texto: str = Field(min_length=3, max_length=4000)
    exemplo_esperado: Optional[str] = Field(default=None, max_length=8000)
    ordem: Optional[int] = Field(default=None, gt=0)
    peso: float = Field(default=1.0, gt=0)
    usa_star: bool = False
    area_tecnica_id: Optional[int] = Field(default=None, gt=0)
    subarea_tecnica_id: Optional[int] = Field(default=None, gt=0)
    codigo: Optional[str] = Field(default=None, min_length=3, max_length=30)
    dificuldade: Optional[str] = Field(default=None, pattern="^(basica|intermediaria|avancada)$")


# Organiza as rotas relacionadas às perguntas.
router = APIRouter(prefix="/perguntas", tags=["Perguntas"])


@router.get("")
def listar(
    somente_ativas: bool = Query(default=True),
    tipo_entrevista_id: Optional[int] = Query(default=None, gt=0),
    competencia_id: Optional[int] = Query(default=None, gt=0),
    area_tecnica_id: Optional[int] = Query(default=None, gt=0),
    subarea_tecnica_id: Optional[int] = Query(default=None, gt=0),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Lista perguntas, aplicando filtros e respeitando o perfil do usuário."""
    # Estudantes não podem consultar perguntas inativas.
    if usuario.perfil != "administrador":
        somente_ativas = True

    try:
        perguntas = listar_perguntas(
            somente_ativas=somente_ativas,
            tipo_entrevista_id=tipo_entrevista_id,
            competencia_id=competencia_id,
            area_tecnica_id=area_tecnica_id,
            subarea_tecnica_id=subarea_tecnica_id
        )
        if usuario.perfil == "administrador":
            return perguntas
        return [replace(pergunta, exemplo_esperado=None) for pergunta in perguntas]
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.get("/{pergunta_id}")
def consultar(
    pergunta_id: int,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Consulta uma pergunta, respeitando a visibilidade de cada perfil."""
    try:
        # Administradores podem consultar perguntas inativas.
        if usuario.perfil == "administrador":
            pergunta = buscar_pergunta(pergunta_id)
        else:
            pergunta = buscar_pergunta_ativa(pergunta_id)

        if pergunta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )

        if usuario.perfil == "administrador":
            return pergunta
        return replace(pergunta, exemplo_esperado=None)

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.post("", status_code=status.HTTP_201_CREATED)
def cadastrar(
    dados: PerguntaCriar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Cadastra uma pergunta após validar seu tipo e seus relacionamentos."""
    try:
        # A competência pode ser nula apenas quando o serviço permitir.
        pergunta = Pergunta(
            tipo_entrevista_id=dados.tipo_entrevista_id,
            competencia_id=dados.competencia_id,
            texto=dados.texto,
            exemplo_esperado=dados.exemplo_esperado,
            ordem=dados.ordem,
            ativa=True,
            peso=dados.peso,
            usa_star=dados.usa_star,
            area_tecnica_id=dados.area_tecnica_id,
            subarea_tecnica_id=dados.subarea_tecnica_id,
            codigo=dados.codigo,
            dificuldade=dados.dificuldade
        )

        pergunta_id = cadastrar_pergunta(pergunta)
        pergunta_criada = buscar_pergunta(pergunta_id)

        if pergunta_criada is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A pergunta foi cadastrada, mas não pôde ser recuperada."
            )

        return pergunta_criada

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{pergunta_id}")
def atualizar(
    pergunta_id: int,
    dados: PerguntaAtualizar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Atualiza uma pergunta preservando seu status e seus dados históricos."""
    try:
        pergunta_atual = buscar_pergunta(pergunta_id)

        if pergunta_atual is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )

        # Os novos campos preservam os valores existentes quando não são enviados.
        # A competência também é preservada quando não aparece na requisição.
        competencia_id = dados.competencia_id
        if "competencia_id" not in dados.model_fields_set:
            competencia_id = pergunta_atual.competencia_id

        pergunta = Pergunta(
            id=pergunta_id,
            tipo_entrevista_id=dados.tipo_entrevista_id,
            competencia_id=competencia_id,
            texto=dados.texto,
            exemplo_esperado=dados.exemplo_esperado,
            ordem=dados.ordem,
            ativa=pergunta_atual.ativa,
            peso=dados.peso,
            usa_star=dados.usa_star,
            area_tecnica_id=dados.area_tecnica_id,
            subarea_tecnica_id=dados.subarea_tecnica_id,
            data_criacao=pergunta_atual.data_criacao,
            codigo=dados.codigo if "codigo" in dados.model_fields_set else pergunta_atual.codigo,
            dificuldade=dados.dificuldade if "dificuldade" in dados.model_fields_set else pergunta_atual.dificuldade
        )

        alterada = editar_pergunta(pergunta_id, pergunta)

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )

        return buscar_pergunta(pergunta_id)

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{pergunta_id}/inativar")
def inativar(
    pergunta_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Inativa uma pergunta sem excluir seu registro do banco."""
    try:
        pergunta = buscar_pergunta(pergunta_id)

        if pergunta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )

        alterada = desativar_pergunta(pergunta_id)

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível inativar a pergunta."
            )

        return buscar_pergunta(pergunta_id)

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{pergunta_id}/ativar")
def ativar(
    pergunta_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Reativa uma pergunta somente quando seus relacionamentos estão válidos."""
    try:
        pergunta = buscar_pergunta(pergunta_id)

        if pergunta is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )

        # A camada de serviço verifica tipo, competência, área e subárea.
        alterada = reativar_pergunta(pergunta_id)

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível ativar a pergunta."
            )

        return buscar_pergunta(pergunta_id)

    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )
