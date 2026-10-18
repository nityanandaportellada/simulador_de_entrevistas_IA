
"""Inicialização da API com configuração de CORS e respostas seguras."""

import logging
import os
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import (
    analise, areas_tecnicas, auth, competencias, criterios, entrevistas,
    historico, perguntas, relatorios, subareas_tecnicas, tipos_entrevista, usuarios
)

logger = logging.getLogger(__name__)
AMBIENTE = os.getenv("APP_ENV", "development").strip().lower()
PRODUCAO = AMBIENTE == "production"
CABECALHOS_SEGUROS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer"
}


def _configurar_origens() -> list[str]:
    """Aceita apenas origens exatas; em produção exige configuração HTTPS."""
    configuracao = os.getenv("CORS_ORIGINS", "")
    if not configuracao.strip():
        if PRODUCAO:
            raise RuntimeError("Configure CORS_ORIGINS com a URL HTTPS do frontend em produção.")
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    origens = []
    for parte in configuracao.split(","):
        origem = parte.strip().rstrip("/")
        url = urlsplit(origem)
        if (
            origem == "*" or url.scheme not in ("http", "https")
            or not url.netloc or url.hostname is None
            or url.path or url.query or url.fragment
            or url.username or url.password
            or (PRODUCAO and url.scheme != "https")
        ):
            raise RuntimeError(f"Origem inválida em CORS_ORIGINS: {origem!r}")
        if origem not in origens:
            origens.append(origem)
    return origens


app = FastAPI(
    title="Simulador de Entrevistas",
    description="API do Simulador de Entrevistas de Emprego Baseado em Inteligência Artificial.",
    version="0.4.0",
    # A documentação interativa permanece acessível durante o desenvolvimento.
    docs_url=None if PRODUCAO else "/docs",
    redoc_url=None if PRODUCAO else "/redoc",
    openapi_url=None if PRODUCAO else "/openapi.json",
    debug=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_configurar_origens(),
    allow_credentials=False,  # A autenticação usa Bearer, não cookies.
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Bootstrap-Token"]
)


@app.middleware("http")
async def cabecalhos_seguranca(request: Request, call_next):
    """Evita cache de dados privados e habilita proteções básicas do navegador."""
    resposta = await call_next(request)
    for nome, valor in CABECALHOS_SEGUROS.items():
        resposta.headers[nome] = valor
    return resposta


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, erro: Exception):
    """Esconde detalhes internos do cliente, mantendo um registro mínimo no servidor."""
    logger.error("Falha inesperada na rota %s (%s)", request.url.path, type(erro).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente novamente mais tarde."},
        headers=CABECALHOS_SEGUROS
    )


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(tipos_entrevista.router)
app.include_router(competencias.router)
app.include_router(criterios.router)
app.include_router(areas_tecnicas.router)
app.include_router(subareas_tecnicas.router)
app.include_router(perguntas.router)
app.include_router(entrevistas.router)
app.include_router(analise.router)
app.include_router(relatorios.router)
app.include_router(historico.router)


@app.get("/", tags=["Sistema"])
def inicio():
    """Informa a versão da aplicação sem expor configurações sensíveis."""
    return {"sistema": "Simulador de Entrevistas", "versao": "0.4.0", "status": "online"}


@app.get("/health", tags=["Sistema"])
def health():
    """Informa que o processo HTTP está disponível, sem consultar dependências."""
    return {"status": "ok"}
