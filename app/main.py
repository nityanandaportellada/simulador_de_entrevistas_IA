"""
main.py

Ponto de entrada da API do
Simulador de Entrevistas.

Versão: 0.4
"""

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# IMPORTAR ROUTERS
# ============================================================

from .routers import (
    auth,
    usuarios,
    tipos_entrevista,
    competencias,
    criterios,
    perguntas,
    entrevistas,
    analise,
    relatorios,
    historico
)


# ============================================================
# CRIAR APLICAÇÃO
# ============================================================

app = FastAPI(

    title="Simulador de Entrevistas",

    description=(
        "API do Simulador de Entrevistas "
        "de Emprego Baseado em "
        "Inteligência Artificial."
    ),

    version="0.4.0"
)


# ============================================================
# CORS
# ============================================================

origens_permitidas = [

    "http://localhost:5173",

    "http://127.0.0.1:5173"
]


app.add_middleware(

    CORSMiddleware,

    allow_origins=origens_permitidas,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# ============================================================
# REGISTRAR ROUTERS
# ============================================================

app.include_router(
    auth.router
)


app.include_router(
    usuarios.router
)


app.include_router(
    tipos_entrevista.router
)


app.include_router(
    competencias.router
)


app.include_router(
    criterios.router
)


app.include_router(
    perguntas.router
)


app.include_router(
    entrevistas.router
)


app.include_router(
    analise.router
)


app.include_router(
    relatorios.router
)


app.include_router(
    historico.router
)


# ============================================================
# ROTA PRINCIPAL
# ============================================================

@app.get(
    "/",
    tags=["Sistema"]
)
def inicio():

    return {

        "sistema":
            "Simulador de Entrevistas",

        "versao":
            "0.4.0",

        "status":
            "online"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get(
    "/health",
    tags=["Sistema"]
)
def health():

    return {

        "status":
            "ok"
    }