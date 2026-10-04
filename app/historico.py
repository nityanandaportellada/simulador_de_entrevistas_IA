"""
historico.py

Serviço responsável pelo histórico de desempenho
do Simulador de Entrevistas.

Versão: 0.3

Responsabilidades:

- listar o histórico de entrevistas do usuário;
- gerar resumo do desempenho;
- apresentar evolução das pontuações;
- apresentar evolução por critério.

Este arquivo contém somente regras de negócio.

Os endpoints HTTP ficam em:

app/routers/historico.py
"""

from .entrevistas import listar_entrevistas_usuario

from .avaliacao import (
    calcular_desempenho_criterios
)


# ============================================================
# FUNÇÃO AUXILIAR
# ============================================================

def _valor(
    objeto,
    atributo,
    padrao=None
):
    """
    Obtém um atributo tanto de objetos
    quanto de dicionários.
    """

    if objeto is None:
        return padrao

    if isinstance(objeto, dict):

        return objeto.get(
            atributo,
            padrao
        )

    return getattr(
        objeto,
        atributo,
        padrao
    )


# ============================================================
# LISTAR HISTÓRICO
# ============================================================

def listar_historico(
    usuario_id: int
) -> list[dict]:
    """
    Retorna o histórico de entrevistas
    pertencentes ao usuário.

    As entrevistas são apresentadas
    da mais recente para a mais antiga.
    """

    if usuario_id <= 0:

        raise ValueError(
            "ID do usuário inválido."
        )


    entrevistas = listar_entrevistas_usuario(
        usuario_id
    )


    historico = []


    for entrevista in entrevistas:

        historico.append(
            {
                "id":
                    _valor(
                        entrevista,
                        "id"
                    ),

                "tipo_entrevista_id":
                    _valor(
                        entrevista,
                        "tipo_entrevista_id"
                    ),

                "data_inicio":
                    _valor(
                        entrevista,
                        "data_inicio"
                    ),

                "data_fim":
                    _valor(
                        entrevista,
                        "data_fim"
                    ),

                "status":
                    _valor(
                        entrevista,
                        "status"
                    ),

                "pontuacao_final":
                    _valor(
                        entrevista,
                        "pontuacao_final"
                    )
            }
        )


    historico.sort(
        key=lambda item:
            item["data_inicio"] or "",
        reverse=True
    )


    return historico


# ============================================================
# GERAR RESUMO DO HISTÓRICO
# ============================================================

def gerar_resumo_historico(
    usuario_id: int
) -> dict:
    """
    Gera indicadores resumidos do histórico
    de entrevistas do usuário.

    Retorna:

    - quantidade total;
    - quantidade avaliada;
    - média das pontuações;
    - melhor pontuação;
    - última pontuação.
    """

    historico = listar_historico(
        usuario_id
    )


    pontuacoes = []


    for entrevista in historico:

        pontuacao = entrevista.get(
            "pontuacao_final"
        )

        if pontuacao is not None:

            pontuacoes.append(
                float(pontuacao)
            )


    quantidade_total = len(
        historico
    )

    quantidade_avaliada = len(
        pontuacoes
    )


    if pontuacoes:

        media = sum(
            pontuacoes
        ) / len(
            pontuacoes
        )

        melhor = max(
            pontuacoes
        )

    else:

        media = None

        melhor = None


    ultima_pontuacao = None


    for entrevista in historico:

        if (
            entrevista[
                "pontuacao_final"
            ]
            is not None
        ):

            ultima_pontuacao = float(
                entrevista[
                    "pontuacao_final"
                ]
            )

            break


    return {

        "quantidade_total":
            quantidade_total,

        "quantidade_avaliada":
            quantidade_avaliada,

        "media_pontuacoes": (
            round(
                media,
                2
            )
            if media is not None
            else None
        ),

        "melhor_pontuacao":
            melhor,

        "ultima_pontuacao":
            ultima_pontuacao
    }


# ============================================================
# EVOLUÇÃO DAS PONTUAÇÕES
# ============================================================

def obter_evolucao_pontuacoes(
    usuario_id: int
) -> list[dict]:
    """
    Retorna a evolução cronológica das
    pontuações do estudante.

    Somente entrevistas que possuem
    pontuação final são consideradas.
    """

    historico = listar_historico(
        usuario_id
    )


    evolucao = []


    for entrevista in historico:

        pontuacao = entrevista.get(
            "pontuacao_final"
        )


        if pontuacao is None:
            continue


        evolucao.append(
            {
                "entrevista_id":
                    entrevista["id"],

                "data":
                    entrevista[
                        "data_fim"
                    ]
                    or
                    entrevista[
                        "data_inicio"
                    ],

                "pontuacao":
                    float(
                        pontuacao
                    )
            }
        )


    # Para gráfico, queremos ordem cronológica:
    # entrevista mais antiga -> mais recente.

    evolucao.sort(
        key=lambda item:
            item["data"] or ""
    )


    return evolucao


# ============================================================
# EVOLUÇÃO POR CRITÉRIO
# ============================================================

def obter_evolucao_criterios(
    usuario_id: int
) -> list[dict]:
    """
    Retorna o desempenho por critério
    ao longo das entrevistas avaliadas.

    Exemplos futuros:

    - Clareza;
    - Objetividade;
    - Coerência;
    - Argumentação;
    - Adequação.
    """

    historico = listar_historico(
        usuario_id
    )


    evolucao = []


    for entrevista in historico:

        entrevista_id = entrevista[
            "id"
        ]


        # Entrevistas ainda sem pontuação
        # não possuem avaliação consolidada.

        if (
            entrevista[
                "pontuacao_final"
            ]
            is None
        ):

            continue


        try:

            criterios = (
                calcular_desempenho_criterios(
                    entrevista_id
                )
            )

        except (
            ValueError,
            TypeError
        ):

            criterios = []


        evolucao.append(
            {
                "entrevista_id":
                    entrevista_id,

                "data":
                    entrevista[
                        "data_fim"
                    ]
                    or
                    entrevista[
                        "data_inicio"
                    ],

                "criterios":
                    criterios
            }
        )


    evolucao.sort(
        key=lambda item:
            item["data"] or ""
    )


    return evolucao