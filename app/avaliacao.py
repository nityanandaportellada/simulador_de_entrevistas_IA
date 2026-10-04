"""
avaliacao.py

Motor de Pontuação do Simulador de Entrevistas.

Versão: 0.5

Responsabilidades:

- recuperar avaliações;
- recuperar notas por critério;
- calcular pontuações;
- calcular desempenho;
- classificar entrevistas;
- identificar destaques;
- atualizar pontuação final.

INTEGRIDADE HISTÓRICA:

Critérios históricos utilizam:

    criterio_nome_aplicado
    criterio_descricao_aplicada
    criterio_ordem_aplicada
    peso_aplicado

Perguntas históricas utilizam:

    peso_pergunta_aplicado

Assim, alterações administrativas futuras não
modificam avaliações antigas.
"""

import sqlite3


try:

    from .database import conectar_banco

except ImportError:

    from database import conectar_banco


NOTA_MINIMA = 0.0

NOTA_MAXIMA = 10.0


CLASSIFICACOES = (

    (
        0.0,
        4.9,
        "Necessita desenvolvimento"
    ),

    (
        5.0,
        6.9,
        "Regular"
    ),

    (
        7.0,
        8.4,
        "Bom"
    ),

    (
        8.5,
        10.0,
        "Muito bom"
    )

)


# ============================================================
# VALIDAR ID
# ============================================================

def _validar_id(
    valor: int,
    nome: str
) -> None:

    if not isinstance(
        valor,
        int
    ):

        raise ValueError(
            f"{nome} inválido."
        )


    if valor <= 0:

        raise ValueError(
            f"{nome} inválido."
        )


# ============================================================
# BUSCAR ENTREVISTA
# ============================================================

def buscar_entrevista(
    entrevista_id: int
) -> dict | None:

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
                usuario_id,
                tipo_entrevista_id,
                tipo_entrevista_nome_aplicado,
                tipo_entrevista_descricao_aplicada,
                data_inicio,
                data_fim,
                status,
                pontuacao_final,
                observacoes

            FROM entrevistas

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return {

            "id":
                registro["id"],

            "usuario_id":
                registro["usuario_id"],

            "tipo_entrevista_id":
                registro[
                    "tipo_entrevista_id"
                ],

            "tipo_entrevista":
                registro[
                    "tipo_entrevista_nome_aplicado"
                ],

            "tipo_entrevista_descricao":
                registro[
                    "tipo_entrevista_descricao_aplicada"
                ],

            "data_inicio":
                registro["data_inicio"],

            "data_fim":
                registro["data_fim"],

            "status":
                registro["status"],

            "pontuacao_final":
                registro[
                    "pontuacao_final"
                ],

            "observacoes":
                registro[
                    "observacoes"
                ]

        }


    finally:

        conexao.close()


# ============================================================
# BUSCAR CRITÉRIOS ATIVOS
# ============================================================

def buscar_criterios_ativos() -> list[dict]:

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
                nome,
                descricao,
                peso,
                ordem

            FROM criterios_avaliacao

            WHERE ativo = 1

            ORDER BY
                COALESCE(
                    ordem,
                    999999
                ),
                id
            """
        )


        registros = (
            cursor.fetchall()
        )


        return [

            {

                "id":
                    registro["id"],

                "nome":
                    registro["nome"],

                "descricao":
                    registro[
                        "descricao"
                    ],

                "peso":
                    registro["peso"],

                "ordem":
                    registro["ordem"]

            }

            for registro in registros

        ]


    finally:

        conexao.close()


# ============================================================
# BUSCAR AVALIAÇÕES
# ============================================================

def buscar_avaliacoes_entrevista(
    entrevista_id: int
) -> list[dict]:

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT

                a.id,

                a.resposta_id,

                a.pontuacao,

                a.pontos_fortes,

                a.pontos_melhoria,

                a.feedback,

                a.modelo_ia,

                a.data_avaliacao,

                r.pergunta_id,

                r.peso_pergunta_aplicado
                    AS peso_pergunta

            FROM avaliacoes a

            INNER JOIN respostas r
                ON r.id = a.resposta_id

            WHERE r.entrevista_id = ?

            ORDER BY

                COALESCE(
                    r.ordem_pergunta_aplicada,
                    999999
                ),

                r.id,

                a.id
            """,
            (
                entrevista_id,
            )
        )


        registros = cursor.fetchall()


        resultados = []


        for registro in registros:

            if registro[
                "peso_pergunta"
            ] is None:

                raise ValueError(
                    "Existe avaliação vinculada "
                    "a resposta sem peso histórico."
                )


            resultados.append(
                {

                    "id":
                        registro["id"],

                    "avaliacao_id":
                        registro["id"],

                    "resposta_id":
                        registro[
                            "resposta_id"
                        ],

                    "pergunta_id":
                        registro[
                            "pergunta_id"
                        ],

                    "pontuacao":
                        registro[
                            "pontuacao"
                        ],

                    "pontos_fortes":
                        registro[
                            "pontos_fortes"
                        ],

                    "pontos_melhoria":
                        registro[
                            "pontos_melhoria"
                        ],

                    "feedback":
                        registro[
                            "feedback"
                        ],

                    "modelo_ia":
                        registro[
                            "modelo_ia"
                        ],

                    "data_avaliacao":
                        registro[
                            "data_avaliacao"
                        ],

                    "peso_pergunta":
                        registro[
                            "peso_pergunta"
                        ]

                }
            )


        return resultados


    finally:

        conexao.close()


# ============================================================
# BUSCAR NOTAS DOS CRITÉRIOS
# ============================================================

def buscar_notas_criterios(
    entrevista_id: int
) -> list[dict]:
    """
    Recupera as notas usando exclusivamente
    os metadados históricos do critério.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT

                ac.avaliacao_id,

                ac.criterio_id,

                ac.nota,

                ac.observacao,

                ac.peso_aplicado
                    AS peso_criterio,

                ac.criterio_nome_aplicado
                    AS criterio,

                ac.criterio_descricao_aplicada
                    AS criterio_descricao,

                ac.criterio_ordem_aplicada
                    AS ordem_criterio,

                r.id
                    AS resposta_id,

                r.pergunta_id,

                r.peso_pergunta_aplicado
                    AS peso_pergunta

            FROM avaliacao_criterios ac

            INNER JOIN avaliacoes a
                ON a.id = ac.avaliacao_id

            INNER JOIN respostas r
                ON r.id = a.resposta_id

            WHERE r.entrevista_id = ?

            ORDER BY

                COALESCE(
                    r.ordem_pergunta_aplicada,
                    999999
                ),

                r.id,

                COALESCE(
                    ac.criterio_ordem_aplicada,
                    999999
                ),

                ac.criterio_id
            """,
            (
                entrevista_id,
            )
        )


        registros = (
            cursor.fetchall()
        )


        resultados = []


        for registro in registros:

            if registro[
                "peso_criterio"
            ] is None:

                raise ValueError(
                    "Existe nota sem peso "
                    "histórico do critério."
                )


            if registro[
                "criterio"
            ] is None:

                raise ValueError(
                    "Existe nota sem nome "
                    "histórico do critério."
                )


            if registro[
                "peso_pergunta"
            ] is None:

                raise ValueError(
                    "Existe nota vinculada a "
                    "resposta sem peso histórico."
                )


            resultados.append(
                {

                    "avaliacao_id":
                        registro[
                            "avaliacao_id"
                        ],

                    "resposta_id":
                        registro[
                            "resposta_id"
                        ],

                    "pergunta_id":
                        registro[
                            "pergunta_id"
                        ],

                    "criterio_id":
                        registro[
                            "criterio_id"
                        ],

                    "criterio":
                        registro[
                            "criterio"
                        ],

                    "criterio_descricao":
                        registro[
                            "criterio_descricao"
                        ],

                    "ordem_criterio":
                        registro[
                            "ordem_criterio"
                        ],

                    "nota":
                        registro[
                            "nota"
                        ],

                    "observacao":
                        registro[
                            "observacao"
                        ],

                    "peso_criterio":
                        registro[
                            "peso_criterio"
                        ],

                    "peso_pergunta":
                        registro[
                            "peso_pergunta"
                        ]

                }
            )


        return resultados


    finally:

        conexao.close()


# ============================================================
# CONTAR RESPOSTAS
# ============================================================

def contar_respostas(
    entrevista_id: int
) -> int:

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM respostas

            WHERE entrevista_id = ?
            """,
            (
                entrevista_id,
            )
        )


        return int(
            cursor.fetchone()[
                "quantidade"
            ]
        )


    finally:

        conexao.close()


# ============================================================
# CONTAR RESPOSTAS AVALIADAS
# ============================================================

def contar_respostas_avaliadas(
    entrevista_id: int
) -> int:

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM avaliacoes a

            INNER JOIN respostas r
                ON r.id = a.resposta_id

            WHERE r.entrevista_id = ?
            """,
            (
                entrevista_id,
            )
        )


        return int(
            cursor.fetchone()[
                "quantidade"
            ]
        )


    finally:

        conexao.close()


# ============================================================
# ENTREVISTA TOTALMENTE AVALIADA
# ============================================================

def entrevista_totalmente_avaliada(
    entrevista_id: int
) -> bool:

    quantidade_respostas = (
        contar_respostas(
            entrevista_id
        )
    )


    quantidade_avaliadas = (
        contar_respostas_avaliadas(
            entrevista_id
        )
    )


    if quantidade_respostas == 0:

        return False


    return (
        quantidade_respostas
        == quantidade_avaliadas
    )


# ============================================================
# PONTUAÇÃO DA RESPOSTA
# ============================================================

def calcular_pontuacao_resposta(
    avaliacao_id: int
) -> float:

    _validar_id(
        avaliacao_id,
        "ID da avaliação"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                nota,
                peso_aplicado AS peso

            FROM avaliacao_criterios

            WHERE avaliacao_id = ?

            ORDER BY
                COALESCE(
                    criterio_ordem_aplicada,
                    999999
                ),
                criterio_id
            """,
            (
                avaliacao_id,
            )
        )


        registros = (
            cursor.fetchall()
        )


        if not registros:

            raise ValueError(
                "A avaliação não possui "
                "notas por critério."
            )


        for registro in registros:

            if registro[
                "peso"
            ] is None:

                raise ValueError(
                    "A avaliação possui critério "
                    "sem peso histórico."
                )


            if registro[
                "peso"
            ] < 0:

                raise ValueError(
                    "O peso histórico do critério "
                    "não pode ser negativo."
                )


        soma_pesos = sum(

            registro[
                "peso"
            ]

            for registro in registros

        )


        if soma_pesos <= 0:

            raise ValueError(
                "A soma dos pesos históricos "
                "deve ser maior que zero."
            )


        pontuacao = sum(

            registro[
                "nota"
            ]
            * registro[
                "peso"
            ]

            for registro in registros

        ) / soma_pesos


        return round(
            pontuacao,
            2
        )


    finally:

        conexao.close()


# ============================================================
# ATUALIZAR PONTUAÇÕES
# ============================================================

def atualizar_pontuacoes_respostas(
    entrevista_id: int
) -> None:

    avaliacoes = (
        buscar_avaliacoes_entrevista(
            entrevista_id
        )
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        for avaliacao in avaliacoes:

            avaliacao_id = (
                avaliacao[
                    "avaliacao_id"
                ]
            )


            pontuacao = (
                calcular_pontuacao_resposta(
                    avaliacao_id
                )
            )


            cursor.execute(
                """
                UPDATE avaliacoes

                SET pontuacao = ?

                WHERE id = ?
                """,
                (
                    pontuacao,
                    avaliacao_id
                )
            )


        conexao.commit()


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# PONTUAÇÃO GERAL
# ============================================================

def calcular_pontuacao_geral(
    entrevista_id: int
) -> float:

    avaliacoes = (
        buscar_avaliacoes_entrevista(
            entrevista_id
        )
    )


    if not avaliacoes:

        raise ValueError(
            "A entrevista não possui avaliações."
        )


    soma_pesos = 0.0

    soma_ponderada = 0.0


    for avaliacao in avaliacoes:

        pontuacao = (
            avaliacao[
                "pontuacao"
            ]
        )


        peso = (
            avaliacao[
                "peso_pergunta"
            ]
        )


        if pontuacao is None:

            raise ValueError(
                "Existe uma resposta sem pontuação."
            )


        if peso is None:

            raise ValueError(
                "Existe resposta sem peso histórico."
            )


        if peso < 0:

            raise ValueError(
                "O peso da pergunta não pode "
                "ser negativo."
            )


        soma_ponderada += (
            pontuacao
            * peso
        )


        soma_pesos += peso


    if soma_pesos <= 0:

        raise ValueError(
            "A soma dos pesos das perguntas "
            "deve ser maior que zero."
        )


    return round(
        soma_ponderada
        / soma_pesos,
        2
    )


# ============================================================
# DESEMPENHO DOS CRITÉRIOS
# ============================================================

def calcular_desempenho_criterios(
    entrevista_id: int
) -> list[dict]:

    notas = (
        buscar_notas_criterios(
            entrevista_id
        )
    )


    if not notas:

        raise ValueError(
            "Não existem notas de critérios "
            "para esta entrevista."
        )


    acumuladores = {}


    for registro in notas:

        criterio_id = (
            registro[
                "criterio_id"
            ]
        )


        if criterio_id not in acumuladores:

            acumuladores[
                criterio_id
            ] = {

                "criterio_id":
                    criterio_id,

                "criterio":
                    registro[
                        "criterio"
                    ],

                "criterio_descricao":
                    registro[
                        "criterio_descricao"
                    ],

                "ordem_criterio":
                    registro[
                        "ordem_criterio"
                    ],

                "peso_criterio":
                    registro[
                        "peso_criterio"
                    ],

                "soma":
                    0.0,

                "soma_pesos":
                    0.0,

                "quantidade":
                    0

            }


        peso_pergunta = (
            registro[
                "peso_pergunta"
            ]
        )


        if peso_pergunta < 0:

            raise ValueError(
                "O peso da pergunta não pode "
                "ser negativo."
            )


        acumuladores[
            criterio_id
        ][
            "soma"
        ] += (
            registro[
                "nota"
            ]
            * peso_pergunta
        )


        acumuladores[
            criterio_id
        ][
            "soma_pesos"
        ] += (
            peso_pergunta
        )


        acumuladores[
            criterio_id
        ][
            "quantidade"
        ] += 1


    resultados = []


    for dados in acumuladores.values():

        if dados[
            "soma_pesos"
        ] <= 0:

            media = 0.0

        else:

            media = (
                dados[
                    "soma"
                ]
                / dados[
                    "soma_pesos"
                ]
            )


        resultados.append(
            {

                "criterio_id":
                    dados[
                        "criterio_id"
                    ],

                "criterio":
                    dados[
                        "criterio"
                    ],

                "criterio_descricao":
                    dados[
                        "criterio_descricao"
                    ],

                "ordem_criterio":
                    dados[
                        "ordem_criterio"
                    ],

                "media":
                    round(
                        media,
                        2
                    ),

                "peso":
                    dados[
                        "peso_criterio"
                    ],

                "quantidade_avaliacoes":
                    dados[
                        "quantidade"
                    ]

            }
        )


    resultados.sort(
        key=lambda item: (
            item[
                "ordem_criterio"
            ]
            if item[
                "ordem_criterio"
            ] is not None
            else 999999,

            item[
                "criterio_id"
            ]
        )
    )


    return resultados


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificar_desempenho(
    pontuacao: float
) -> str:

    if (
        pontuacao < NOTA_MINIMA
        or pontuacao > NOTA_MAXIMA
    ):

        raise ValueError(
            "A pontuação deve estar entre 0 e 10."
        )


    if pontuacao < 5.0:

        return (
            "Necessita desenvolvimento"
        )


    if pontuacao < 7.0:

        return "Regular"


    if pontuacao < 8.5:

        return "Bom"


    return "Muito bom"


# ============================================================
# DESTAQUES
# ============================================================

def identificar_destaques(
    desempenho_criterios: list[dict]
) -> dict:

    if not desempenho_criterios:

        return {

            "melhor_criterio":
                None,

            "criterio_a_desenvolver":
                None

        }


    melhor = max(

        desempenho_criterios,

        key=lambda item:
            item[
                "media"
            ]

    )


    menor = min(

        desempenho_criterios,

        key=lambda item:
            item[
                "media"
            ]

    )


    return {

        "melhor_criterio": {

            "criterio":
                melhor[
                    "criterio"
                ],

            "media":
                melhor[
                    "media"
                ]

        },

        "criterio_a_desenvolver": {

            "criterio":
                menor[
                    "criterio"
                ],

            "media":
                menor[
                    "media"
                ]

        }

    }


# ============================================================
# ATUALIZAR RESULTADO
# ============================================================

def atualizar_resultado_entrevista(
    entrevista_id: int,
    pontuacao_final: float
) -> None:

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    if (
        pontuacao_final < NOTA_MINIMA
        or pontuacao_final > NOTA_MAXIMA
    ):

        raise ValueError(
            "Pontuação final inválida."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE entrevistas

            SET
                pontuacao_final = ?,
                status = 'avaliada'

            WHERE id = ?
            """,
            (
                pontuacao_final,
                entrevista_id
            )
        )


        if cursor.rowcount == 0:

            raise ValueError(
                "Entrevista não encontrada."
            )


        conexao.commit()


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# PROCESSAR AVALIAÇÃO
# ============================================================

def processar_avaliacao(
    entrevista_id: int
) -> dict:

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    entrevista = buscar_entrevista(
        entrevista_id
    )


    if entrevista is None:

        raise ValueError(
            "Entrevista não encontrada."
        )


    if entrevista[
        "status"
    ] not in (

        "em_analise",

        "finalizada",

        "avaliada",

        "erro_analise"

    ):

        raise ValueError(
            "A entrevista não está em um estado "
            "válido para processamento."
        )


    if not entrevista_totalmente_avaliada(
        entrevista_id
    ):

        raise ValueError(
            "Nem todas as respostas da entrevista "
            "foram avaliadas."
        )


    atualizar_pontuacoes_respostas(
        entrevista_id
    )


    pontuacao_final = (
        calcular_pontuacao_geral(
            entrevista_id
        )
    )


    desempenho_criterios = (
        calcular_desempenho_criterios(
            entrevista_id
        )
    )


    classificacao = (
        classificar_desempenho(
            pontuacao_final
        )
    )


    destaques = (
        identificar_destaques(
            desempenho_criterios
        )
    )


    atualizar_resultado_entrevista(
        entrevista_id,
        pontuacao_final
    )


    return {

        "entrevista_id":
            entrevista_id,

        "pontuacao_final":
            pontuacao_final,

        "classificacao":
            classificacao,

        "desempenho_criterios":
            desempenho_criterios,

        "melhor_criterio":
            destaques[
                "melhor_criterio"
            ],

        "criterio_a_desenvolver":
            destaques[
                "criterio_a_desenvolver"
            ]

    }