"""
main.py

Ponto de entrada da API do
Simulador de Entrevistas.

A aplicação disponibiliza:

- autenticação;
- usuários;
- tipos de entrevista;
- competências;
- critérios;
- áreas técnicas;
- subáreas técnicas;
- perguntas;
- entrevistas;
- análise;
- relatórios;
- histórico.

Versão da API: 0.4.0
"""

from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware
)


# ============================================================
# IMPORTAR ROUTERS
# ============================================================

from .routers import (

    auth,

    usuarios,

    tipos_entrevista,

    competencias,

    criterios,

    areas_tecnicas,

    subareas_tecnicas,

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

    title=(
        "Simulador de Entrevistas"
    ),

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

    allow_origins=(
        origens_permitidas
    ),

    allow_credentials=True,

    allow_methods=[
        "*"
    ],

    allow_headers=[
        "*"
    ]

)


# ============================================================
# REGISTRAR AUTENTICAÇÃO
# ============================================================

app.include_router(
    auth.router
)


# ============================================================
# REGISTRAR USUÁRIOS
# ============================================================

app.include_router(
    usuarios.router
)


# ============================================================
# REGISTRAR TIPOS DE ENTREVISTA
# ============================================================

app.include_router(
    tipos_entrevista.router
)


# ============================================================
# REGISTRAR COMPETÊNCIAS
# ============================================================

app.include_router(
    competencias.router
)


# ============================================================
# REGISTRAR CRITÉRIOS
# ============================================================

app.include_router(
    criterios.router
)


# ============================================================
# REGISTRAR ÁREAS TÉCNICAS
# ============================================================

app.include_router(
    areas_tecnicas.router
)


# ============================================================
# REGISTRAR SUBÁREAS TÉCNICAS
# ============================================================

app.include_router(
    subareas_tecnicas.router
)


# ============================================================
# REGISTRAR PERGUNTAS
# ============================================================

app.include_router(
    perguntas.router
)


# ============================================================
# REGISTRAR ENTREVISTAS
# ============================================================

app.include_router(
    entrevistas.router
)


# ============================================================
# REGISTRAR ANÁLISE
# ============================================================

app.include_router(
    analise.router
)


# ============================================================
# REGISTRAR RELATÓRIOS
# ============================================================

app.include_router(
    relatorios.router
)


# ============================================================
# REGISTRAR HISTÓRICO
# ============================================================

app.include_router(
    historico.router
)


# ============================================================
# ROTA PRINCIPAL
# ============================================================

@app.get(
    "/",
    tags=[
        "Sistema"
    ]
)
def inicio():
    """
    Retorna informações básicas
    sobre a aplicação.
    """

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
    tags=[
        "Sistema"
    ]
)
def health():
    """
    Endpoint simples utilizado
    para verificar a disponibilidade da API.
    """

    return {

        "status":
            "ok"

    }