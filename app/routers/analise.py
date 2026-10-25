
"""Rotas protegidas para avaliação de entrevistas com controle de cotas e recuperação."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from ..analise import analisar_entrevista
from ..controle_analises import (
    AnaliseEmAndamentoError, finalizar_monitoramento,
    recuperar_analise_interrompida, registrar_inicio_analise
)
from ..database import conectar_banco
from ..limites_analise import LimiteAnaliseError, obter_configuracoes_ia, salvar_configuracoes_ia
from ..models import Usuario
from ..security import obter_usuario_atual, obter_administrador_atual

router = APIRouter(prefix="/analise", tags=["Análise"])
logger = logging.getLogger(__name__)


def verificar_acesso_entrevista(entrevista_id: int, usuario: Usuario):
    """Consulta a entrevista sem revelar a estudantes IDs pertencentes a terceiros."""
    if entrevista_id <= 0:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada.")
    conexao = conectar_banco()
    try:
        entrevista = conexao.execute(
            "SELECT id, usuario_id, status FROM entrevistas WHERE id = ?", (entrevista_id,)
        ).fetchone()
    finally:
        conexao.close()
    if entrevista is None or (usuario.perfil != "administrador" and entrevista["usuario_id"] != usuario.id):
        raise HTTPException(status_code=404, detail="Entrevista não encontrada.")
    return entrevista


class ConfiguracoesIARequest(BaseModel):
    """Parâmetros que podem ser alterados por um administrador."""
    model_config = ConfigDict(extra="forbid")
    limite_usuario_dia: int = Field(ge=1, le=100000, strict=True)
    limite_global_dia: int = Field(ge=1, le=100000, strict=True)
    limite_entrevista: int = Field(ge=1, le=100000, strict=True)
    retencao_dias: int = Field(ge=30, le=365, strict=True)


@router.get("/admin/configuracoes")
def consultar_configuracoes_ia(administrador: Usuario = Depends(obter_administrador_atual)):
    """Consulta limites efetivos sem expor chaves ou respostas dos estudantes."""
    return obter_configuracoes_ia()


@router.put("/admin/configuracoes")
def alterar_configuracoes_ia(dados: ConfiguracoesIARequest, administrador: Usuario = Depends(obter_administrador_atual)):
    """Persiste alterações e preserva as chamadas anteriormente reservadas."""
    try:
        configuracoes = salvar_configuracoes_ia(
            dados.limite_usuario_dia, dados.limite_global_dia,
            dados.limite_entrevista, dados.retencao_dias, administrador.id
        )
        logger.info("Limites da IA alterados pelo administrador %s", administrador.id)
        return configuracoes
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.post("/entrevistas/{entrevista_id}")
def executar_analise_entrevista(entrevista_id: int, usuario: Usuario = Depends(obter_usuario_atual)):
    """Analisa entrevistas, respeita cotas e permite recuperar execuções interrompidas."""
    entrevista = verificar_acesso_entrevista(entrevista_id, usuario)
    monitoramento_iniciado = False
    try:
        if entrevista["status"] == "em_analise":
            recuperar_analise_interrompida(entrevista_id)
            entrevista = verificar_acesso_entrevista(entrevista_id, usuario)
        if entrevista["status"] not in ("finalizada", "erro_analise"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A entrevista precisa estar finalizada ou com erro de análise."
            )
        registrar_inicio_analise(entrevista_id)
        monitoramento_iniciado = True
        # A reserva e o limite de chamadas são validados novamente no serviço.
        return analisar_entrevista(entrevista_id)
    except LimiteAnaliseError as erro:
        cabecalhos = {"Retry-After": str(erro.retry_after)} if erro.retry_after is not None else None
        raise HTTPException(status_code=429, detail=str(erro), headers=cabecalhos) from erro
    except AnaliseEmAndamentoError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except RuntimeError as erro:
        logger.error("Serviço de análise indisponível para entrevista %s (%s)", entrevista_id, type(erro).__name__)
        raise HTTPException(
            status_code=503, detail="Serviço de análise indisponível no momento."
        ) from erro
    except Exception as erro:
        logger.error("Falha inesperada na análise da entrevista %s (%s)", entrevista_id, type(erro).__name__)
        raise HTTPException(
            status_code=500, detail="Não foi possível concluir a análise. Tente novamente mais tarde."
        ) from erro
    finally:
        if monitoramento_iniciado:
            finalizar_monitoramento(entrevista_id)
