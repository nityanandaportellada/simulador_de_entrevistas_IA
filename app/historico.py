"""
historico.py

Serviço responsável pelo histórico de entrevistas
do Simulador de Entrevistas.

Versão: 0.7

Responsabilidades:

- listar entrevistas anteriores do estudante;
- apresentar tipo de entrevista histórico;
- apresentar área e subárea histórica;
- gerar resumo de desempenho;
- apresentar evolução das pontuações;
- apresentar evolução por critérios;
- preservar os dados históricos das entrevistas.

IMPORTANTE:

O histórico não consulta os nomes atuais dos
tipos, áreas ou subáreas para reconstruir
entrevistas antigas.

São utilizados os snapshots armazenados
na própria entrevista.

Assim:

- renomear uma área não modifica o passado;
- renomear uma subárea não modifica o passado;
- editar o tipo de entrevista não modifica o passado.

Também não são escondidos erros de integridade.

Caso o Motor de Pontuação identifique dados históricos
inconsistentes, o erro será propagado para que o problema
possa ser diagnosticado corretamente.
"""

from .database import (
    conectar_banco
)


from .avaliacao import (
    calcular_desempenho_criterios
)


# ============================================================
# VALIDAR ID
# ============================================================

def _validar_id(
    valor: int,
    campo: str
) -> None:
    """
    Valida identificadores numéricos.
    """

    if not isinstance(
        valor,
        int
    ):

        raise ValueError(
            f"{campo} inválido."
        )


    if valor <= 0:

        raise ValueError(
            f"{campo} inválido."
        )


# ============================================================
# LISTAR HISTÓRICO
# ============================================================

def listar_historico(
    usuario_id: int
) -> list[dict]:
    """
    Retorna todas as entrevistas pertencentes
    ao usuário.

    As mais recentes aparecem primeiro.

    Também retorna o contexto histórico
    da entrevista técnica quando aplicável.
    """

    _validar_id(
        usuario_id,
        "ID do usuário"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT

                id,

                tipo_entrevista_id,

                tipo_entrevista_nome_aplicado,

                area_tecnica_id,

                area_tecnica_nome_aplicado,

                subarea_tecnica_id,

                subarea_tecnica_nome_aplicado,

                data_inicio,

                data_fim,

                status,

                pontuacao_final

            FROM entrevistas

            WHERE usuario_id = ?

            ORDER BY

                data_inicio DESC,

                id DESC
            """,
            (
                usuario_id,
            )
        )


        registros = cursor.fetchall()


        return [

            {

                "id":
                    registro[
                        "id"
                    ],

                "tipo_entrevista_id":
                    registro[
                        "tipo_entrevista_id"
                    ],

                "tipo_entrevista":
                    registro[
                        "tipo_entrevista_nome_aplicado"
                    ],

                "area_tecnica_id":
                    registro[
                        "area_tecnica_id"
                    ],

                "area_tecnica":
                    registro[
                        "area_tecnica_nome_aplicado"
                    ],

                "subarea_tecnica_id":
                    registro[
                        "subarea_tecnica_id"
                    ],

                "subarea_tecnica":
                    registro[
                        "subarea_tecnica_nome_aplicado"
                    ],

                "data_inicio":
                    registro[
                        "data_inicio"
                    ],

                "data_fim":
                    registro[
                        "data_fim"
                    ],

                "status":
                    registro[
                        "status"
                    ],

                "pontuacao_final":
                    registro[
                        "pontuacao_final"
                    ]

            }

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# GERAR RESUMO
# ============================================================

def gerar_resumo_historico(
    usuario_id: int
) -> dict:
    """
    Gera um resumo das entrevistas realizadas
    pelo usuário.

    Mantém o contrato utilizado pelo frontend:

    - quantidade_total;
    - quantidade_avaliada;
    - media_pontuacoes;
    - melhor_pontuacao;
    - ultima_pontuacao.
    """

    _validar_id(
        usuario_id,
        "ID do usuário"
    )


    historico = listar_historico(
        usuario_id
    )


    quantidade_total = len(
        historico
    )


    entrevistas_avaliadas = [

        entrevista

        for entrevista
        in historico

        if (

            entrevista[
                "status"
            ]
            == "avaliada"

            and

            entrevista[
                "pontuacao_final"
            ]
            is not None

        )

    ]


    quantidade_avaliada = len(
        entrevistas_avaliadas
    )


    pontuacoes = [

        float(
            entrevista[
                "pontuacao_final"
            ]
        )

        for entrevista
        in entrevistas_avaliadas

    ]


    if pontuacoes:

        media_pontuacoes = round(

            sum(
                pontuacoes
            )
            /
            len(
                pontuacoes
            ),

            2

        )


        melhor_pontuacao = round(

            max(
                pontuacoes
            ),

            2

        )


        # ----------------------------------------------------
        # O histórico está ordenado do mais recente
        # para o mais antigo.
        # ----------------------------------------------------

        ultima_pontuacao = round(

            pontuacoes[
                0
            ],

            2

        )


    else:

        media_pontuacoes = None

        melhor_pontuacao = None

        ultima_pontuacao = None


    return {

        "quantidade_total":
            quantidade_total,

        "quantidade_avaliada":
            quantidade_avaliada,

        "media_pontuacoes":
            media_pontuacoes,

        "melhor_pontuacao":
            melhor_pontuacao,

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

    Somente entrevistas avaliadas e com
    pontuação final são consideradas.
    """

    _validar_id(
        usuario_id,
        "ID do usuário"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT

                id,

                tipo_entrevista_id,

                tipo_entrevista_nome_aplicado,

                area_tecnica_id,

                area_tecnica_nome_aplicado,

                subarea_tecnica_id,

                subarea_tecnica_nome_aplicado,

                data_inicio,

                data_fim,

                pontuacao_final

            FROM entrevistas

            WHERE
                usuario_id = ?

              AND
                status = 'avaliada'

              AND
                pontuacao_final IS NOT NULL

            ORDER BY

                COALESCE(
                    data_fim,
                    data_inicio
                ),

                id
            """,
            (
                usuario_id,
            )
        )


        registros = cursor.fetchall()


        return [

            {

                "entrevista_id":
                    registro[
                        "id"
                    ],

                "data":
                    (
                        registro[
                            "data_fim"
                        ]
                        or
                        registro[
                            "data_inicio"
                        ]
                    ),

                "pontuacao":
                    registro[
                        "pontuacao_final"
                    ],

                "tipo_entrevista_id":
                    registro[
                        "tipo_entrevista_id"
                    ],

                "tipo_entrevista":
                    registro[
                        "tipo_entrevista_nome_aplicado"
                    ],

                "area_tecnica_id":
                    registro[
                        "area_tecnica_id"
                    ],

                "area_tecnica":
                    registro[
                        "area_tecnica_nome_aplicado"
                    ],

                "subarea_tecnica_id":
                    registro[
                        "subarea_tecnica_id"
                    ],

                "subarea_tecnica":
                    registro[
                        "subarea_tecnica_nome_aplicado"
                    ]

            }

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# ENTREVISTAS AVALIADAS
# ============================================================

def _listar_entrevistas_avaliadas(
    usuario_id: int
) -> list[dict]:
    """
    Retorna entrevistas avaliadas em ordem
    cronológica para utilização na evolução
    por critérios.
    """

    _validar_id(
        usuario_id,
        "ID do usuário"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT

                id,

                tipo_entrevista_id,

                tipo_entrevista_nome_aplicado,

                area_tecnica_id,

                area_tecnica_nome_aplicado,

                subarea_tecnica_id,

                subarea_tecnica_nome_aplicado,

                data_inicio,

                data_fim,

                pontuacao_final

            FROM entrevistas

            WHERE
                usuario_id = ?

              AND
                status = 'avaliada'

            ORDER BY

                COALESCE(
                    data_fim,
                    data_inicio
                ),

                id
            """,
            (
                usuario_id,
            )
        )


        registros = cursor.fetchall()


        return [

            {

                "id":
                    registro[
                        "id"
                    ],

                "tipo_entrevista_id":
                    registro[
                        "tipo_entrevista_id"
                    ],

                "tipo_entrevista":
                    registro[
                        "tipo_entrevista_nome_aplicado"
                    ],

                "area_tecnica_id":
                    registro[
                        "area_tecnica_id"
                    ],

                "area_tecnica":
                    registro[
                        "area_tecnica_nome_aplicado"
                    ],

                "subarea_tecnica_id":
                    registro[
                        "subarea_tecnica_id"
                    ],

                "subarea_tecnica":
                    registro[
                        "subarea_tecnica_nome_aplicado"
                    ],

                "data_inicio":
                    registro[
                        "data_inicio"
                    ],

                "data_fim":
                    registro[
                        "data_fim"
                    ],

                "pontuacao_final":
                    registro[
                        "pontuacao_final"
                    ]

            }

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# EVOLUÇÃO DOS CRITÉRIOS
# ============================================================

def obter_evolucao_criterios(
    usuario_id: int
) -> list[dict]:
    """
    Retorna a evolução dos critérios
    ao longo das entrevistas avaliadas.

    IMPORTANTÍSSIMO:

    Não existe tratamento silencioso de erro
    nesta função.

    Se calcular_desempenho_criterios identificar
    inconsistência histórica, o erro será propagado.

    Isso evita apresentar:

        "criterios": []

    quando, na realidade, existe problema nos dados.
    """

    _validar_id(
        usuario_id,
        "ID do usuário"
    )


    entrevistas = (
        _listar_entrevistas_avaliadas(
            usuario_id
        )
    )


    evolucao = []


    for entrevista in entrevistas:

        entrevista_id = entrevista[
            "id"
        ]


        # ====================================================
        # NÃO ESCONDER ERROS DE INTEGRIDADE
        # ====================================================

        criterios = (
            calcular_desempenho_criterios(
                entrevista_id
            )
        )


        evolucao.append(

            {

                "entrevista_id":
                    entrevista_id,

                "data":
                    (
                        entrevista[
                            "data_fim"
                        ]
                        or
                        entrevista[
                            "data_inicio"
                        ]
                    ),

                "tipo_entrevista_id":
                    entrevista[
                        "tipo_entrevista_id"
                    ],

                "tipo_entrevista":
                    entrevista[
                        "tipo_entrevista"
                    ],

                "area_tecnica_id":
                    entrevista[
                        "area_tecnica_id"
                    ],

                "area_tecnica":
                    entrevista[
                        "area_tecnica"
                    ],

                "subarea_tecnica_id":
                    entrevista[
                        "subarea_tecnica_id"
                    ],

                "subarea_tecnica":
                    entrevista[
                        "subarea_tecnica"
                    ],

                "criterios":
                    criterios

            }

        )


    return evolucao