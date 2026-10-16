"""
avaliacao.py

Motor de Pontuação do Simulador de Entrevistas.

Versão: 0.6

Responsabilidades:

- recuperar avaliações;
- recuperar notas por critério;
- calcular pontuações das respostas;
- calcular pontuação geral da entrevista;
- calcular desempenho por critério;
- classificar entrevistas;
- identificar destaques;
- atualizar pontuação final;
- preservar a integridade histórica dos cálculos.

INTEGRIDADE HISTÓRICA:

Critérios históricos utilizam:

    criterio_nome_aplicado
    criterio_descricao_aplicada
    criterio_ordem_aplicada
    peso_aplicado

Perguntas históricas utilizam:

    peso_pergunta_aplicado

A identificação histórica da entrevista utiliza:

    tipo_entrevista_nome_aplicado
    tipo_entrevista_descricao_aplicada
    area_tecnica_nome_aplicado
    subarea_tecnica_nome_aplicado

IMPORTANTE:

Área e subárea técnica contextualizam a entrevista,
mas NÃO alteram diretamente a fórmula matemática
da pontuação.

A pontuação continua sendo determinada por:

- notas dos critérios;
- pesos históricos dos critérios;
- peso histórico de cada pergunta.

Assim, alterações administrativas futuras em:

- critérios;
- pesos;
- perguntas;
- tipos de entrevista;
- áreas;
- subáreas;

não modificam avaliações antigas.
"""

import sqlite3


try:

    from .database import conectar_banco

except ImportError:

    from database import conectar_banco


# ============================================================
# ESCALA DE PONTUAÇÃO
# ============================================================

NOTA_MINIMA = 0.0

NOTA_MAXIMA = 10.0


# ============================================================
# CLASSIFICAÇÕES
# ============================================================

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
    """
    Valida identificadores utilizados pelo
    Motor de Pontuação.
    """

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
# VALIDAR NOTA
# ============================================================

def _validar_nota(
    valor,
    nome: str = "Nota"
) -> float:
    """
    Converte e valida uma nota na escala
    de 0 até 10.
    """

    try:

        nota = float(
            valor
        )

    except (
        TypeError,
        ValueError
    ) as erro:

        raise ValueError(
            f"{nome} inválida."
        ) from erro


    if (
        nota < NOTA_MINIMA
        or nota > NOTA_MAXIMA
    ):

        raise ValueError(
            f"{nome} deve estar entre 0 e 10."
        )


    return nota


# ============================================================
# VALIDAR PESO
# ============================================================

def _validar_peso(
    valor,
    nome: str
) -> float:
    """
    Converte e valida um peso histórico.

    Um peso individual pode ser zero.

    Entretanto, a soma dos pesos utilizados
    em determinado cálculo deve ser maior
    que zero.
    """

    if valor is None:

        raise ValueError(
            f"{nome} não informado."
        )


    try:

        peso = float(
            valor
        )

    except (
        TypeError,
        ValueError
    ) as erro:

        raise ValueError(
            f"{nome} inválido."
        ) from erro


    if peso < 0:

        raise ValueError(
            f"{nome} não pode ser negativo."
        )


    return peso


# ============================================================
# BUSCAR ENTREVISTA
# ============================================================

def buscar_entrevista(
    entrevista_id: int
) -> dict | None:
    """
    Recupera os dados históricos da entrevista.

    Tipo, área e subárea são retornados
    utilizando os snapshots armazenados
    na própria entrevista.

    Isso impede que alterações administrativas
    posteriores modifiquem a identificação
    histórica da entrevista.
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

                id,

                usuario_id,

                tipo_entrevista_id,

                tipo_entrevista_nome_aplicado,

                tipo_entrevista_descricao_aplicada,

                area_tecnica_id,

                area_tecnica_nome_aplicado,

                subarea_tecnica_id,

                subarea_tecnica_nome_aplicado,

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
                registro[
                    "id"
                ],

            "usuario_id":
                registro[
                    "usuario_id"
                ],

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
    """
    Recupera os critérios administrativos
    atualmente ativos.

    IMPORTANTE:

    Esta função representa o estado ATUAL
    do cadastro de critérios.

    Ela não é utilizada para recalcular
    avaliações históricas.

    Os cálculos históricos utilizam os
    snapshots existentes em:

        avaliacao_criterios
    """

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


        registros = cursor.fetchall()


        return [

            {

                "id":
                    registro[
                        "id"
                    ],

                "nome":
                    registro[
                        "nome"
                    ],

                "descricao":
                    registro[
                        "descricao"
                    ],

                "peso":
                    registro[
                        "peso"
                    ],

                "ordem":
                    registro[
                        "ordem"
                    ]

            }

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# BUSCAR AVALIAÇÕES
# ============================================================

def buscar_avaliacoes_entrevista(
    entrevista_id: int
) -> list[dict]:
    """
    Recupera todas as avaliações pertencentes
    à entrevista.

    O peso da pergunta é obtido exclusivamente
    do snapshot:

        respostas.peso_pergunta_aplicado

    Nenhuma consulta ao peso atual da tabela
    perguntas é realizada.
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

            peso_pergunta = _validar_peso(

                registro[
                    "peso_pergunta"
                ],

                "Peso histórico da pergunta"

            )


            pontuacao = registro[
                "pontuacao"
            ]


            if pontuacao is not None:

                pontuacao = _validar_nota(

                    pontuacao,

                    "Pontuação da resposta"

                )


            resultados.append(
                {

                    "id":
                        registro[
                            "id"
                        ],

                    "avaliacao_id":
                        registro[
                            "id"
                        ],

                    "resposta_id":
                        registro[
                            "resposta_id"
                        ],

                    "pergunta_id":
                        registro[
                            "pergunta_id"
                        ],

                    "pontuacao":
                        pontuacao,

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
                        peso_pergunta

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
    Recupera as notas utilizando exclusivamente
    os snapshots históricos dos critérios
    e das perguntas.

    São utilizados:

        peso_aplicado
        criterio_nome_aplicado
        criterio_descricao_aplicada
        criterio_ordem_aplicada
        peso_pergunta_aplicado

    Nenhum nome, descrição ou peso atual dos
    cadastros administrativos é utilizado.
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


        registros = cursor.fetchall()


        resultados = []


        for registro in registros:

            # =================================================
            # VALIDAR NOME HISTÓRICO
            # =================================================

            if (
                registro[
                    "criterio"
                ]
                is None
            ):

                raise ValueError(
                    "Existe nota sem nome histórico "
                    "do critério."
                )


            # =================================================
            # VALIDAR NOTA
            # =================================================

            nota = _validar_nota(

                registro[
                    "nota"
                ],

                "Nota do critério"

            )


            # =================================================
            # VALIDAR PESO DO CRITÉRIO
            # =================================================

            peso_criterio = _validar_peso(

                registro[
                    "peso_criterio"
                ],

                "Peso histórico do critério"

            )


            # =================================================
            # VALIDAR PESO DA PERGUNTA
            # =================================================

            peso_pergunta = _validar_peso(

                registro[
                    "peso_pergunta"
                ],

                "Peso histórico da pergunta"

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
                        nota,

                    "observacao":
                        registro[
                            "observacao"
                        ],

                    "peso_criterio":
                        peso_criterio,

                    "peso_pergunta":
                        peso_pergunta

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
    """
    Retorna a quantidade de respostas
    existentes na entrevista.
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
                COUNT(*) AS quantidade

            FROM respostas

            WHERE entrevista_id = ?
            """,
            (
                entrevista_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro[
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
    """
    Retorna quantas respostas distintas
    possuem avaliação.

    COUNT(DISTINCT resposta_id) evita que
    eventual inconsistência ou duplicidade
    seja interpretada como outra resposta.
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

                COUNT(
                    DISTINCT a.resposta_id
                ) AS quantidade

            FROM avaliacoes a

            INNER JOIN respostas r
                ON r.id = a.resposta_id

            WHERE r.entrevista_id = ?
            """,
            (
                entrevista_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro[
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
    """
    Verifica se todas as respostas existentes
    possuem avaliação.
    """

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
    """
    Calcula a pontuação consolidada
    de uma resposta.

    São utilizadas somente:

    - notas históricas;
    - pesos históricos dos critérios.

    A tabela criterios_avaliacao não participa
    deste cálculo.
    """

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

                peso_aplicado
                    AS peso

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


        registros = cursor.fetchall()


        if not registros:

            raise ValueError(
                "A avaliação não possui "
                "notas por critério."
            )


        soma_pesos = 0.0

        soma_ponderada = 0.0


        for registro in registros:

            # =================================================
            # NOTA
            # =================================================

            nota = _validar_nota(

                registro[
                    "nota"
                ],

                "Nota do critério"

            )


            # =================================================
            # PESO
            # =================================================

            peso = _validar_peso(

                registro[
                    "peso"
                ],

                "Peso histórico do critério"

            )


            soma_ponderada += (
                nota
                *
                peso
            )


            soma_pesos += peso


        if soma_pesos <= 0:

            raise ValueError(
                "A soma dos pesos históricos "
                "dos critérios deve ser maior que zero."
            )


        return round(

            soma_ponderada
            /
            soma_pesos,

            2

        )


    finally:

        conexao.close()


# ============================================================
# ATUALIZAR PONTUAÇÕES DAS RESPOSTAS
# ============================================================

def atualizar_pontuacoes_respostas(
    entrevista_id: int
) -> None:
    """
    Recalcula a pontuação armazenada
    em cada avaliação.

    Todos os cálculos são realizados primeiro.

    Somente depois o banco é atualizado.

    Isso evita atualizações parciais caso algum
    snapshot histórico esteja inconsistente.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    avaliacoes = (
        buscar_avaliacoes_entrevista(
            entrevista_id
        )
    )


    if not avaliacoes:

        raise ValueError(
            "A entrevista não possui avaliações."
        )


    pontuacoes = []


    # ========================================================
    # CALCULAR TODAS AS PONTUAÇÕES ANTES DO UPDATE
    # ========================================================

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


        pontuacoes.append(
            (
                pontuacao,
                avaliacao_id
            )
        )


    # ========================================================
    # ATUALIZAR EM TRANSAÇÃO
    # ========================================================

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        for (
            pontuacao,
            avaliacao_id
        ) in pontuacoes:

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


            if cursor.rowcount != 1:

                raise ValueError(
                    "Não foi possível atualizar "
                    "uma das avaliações."
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
    """
    Calcula a pontuação geral da entrevista.

    A pontuação de cada resposta é ponderada
    pelo peso histórico da pergunta:

        respostas.peso_pergunta_aplicado

    O peso atual da tabela perguntas não
    participa do cálculo.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


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

        # ====================================================
        # PONTUAÇÃO DA RESPOSTA
        # ====================================================

        pontuacao = _validar_nota(

            avaliacao[
                "pontuacao"
            ],

            "Pontuação da resposta"

        )


        # ====================================================
        # PESO HISTÓRICO DA PERGUNTA
        # ====================================================

        peso = _validar_peso(

            avaliacao[
                "peso_pergunta"
            ],

            "Peso histórico da pergunta"

        )


        soma_ponderada += (
            pontuacao
            *
            peso
        )


        soma_pesos += peso


    if soma_pesos <= 0:

        raise ValueError(
            "A soma dos pesos históricos "
            "das perguntas deve ser maior que zero."
        )


    return round(

        soma_ponderada
        /
        soma_pesos,

        2

    )


# ============================================================
# DESEMPENHO DOS CRITÉRIOS
# ============================================================

def calcular_desempenho_criterios(
    entrevista_id: int
) -> list[dict]:
    """
    Calcula o desempenho médio de cada
    critério na entrevista.

    As notas de cada critério são ponderadas
    pelo peso histórico da pergunta.

    Os dados apresentados também utilizam
    snapshots:

    - nome;
    - descrição;
    - ordem;
    - peso do critério.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


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


        # ====================================================
        # PRIMEIRA OCORRÊNCIA DO CRITÉRIO
        # ====================================================

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


        else:

            # =================================================
            # VALIDAR CONSISTÊNCIA DO SNAPSHOT
            # =================================================
            #
            # Dentro de uma mesma entrevista,
            # o mesmo critério deve possuir os
            # mesmos dados históricos.
            # =================================================

            dados_existentes = (
                acumuladores[
                    criterio_id
                ]
            )


            if (

                dados_existentes[
                    "criterio"
                ]
                != registro[
                    "criterio"
                ]

                or

                dados_existentes[
                    "criterio_descricao"
                ]
                != registro[
                    "criterio_descricao"
                ]

                or

                dados_existentes[
                    "ordem_criterio"
                ]
                != registro[
                    "ordem_criterio"
                ]

                or

                dados_existentes[
                    "peso_criterio"
                ]
                != registro[
                    "peso_criterio"
                ]

            ):

                raise ValueError(
                    "Foram encontrados snapshots históricos "
                    "inconsistentes para o mesmo critério "
                    "dentro da entrevista."
                )


        # ====================================================
        # PESO HISTÓRICO DA PERGUNTA
        # ====================================================

        peso_pergunta = _validar_peso(

            registro[
                "peso_pergunta"
            ],

            "Peso histórico da pergunta"

        )


        # ====================================================
        # NOTA DO CRITÉRIO
        # ====================================================

        nota = _validar_nota(

            registro[
                "nota"
            ],

            "Nota do critério"

        )


        # ====================================================
        # ACUMULAR
        # ====================================================

        acumuladores[
            criterio_id
        ][
            "soma"
        ] += (
            nota
            *
            peso_pergunta
        )


        acumuladores[
            criterio_id
        ][
            "soma_pesos"
        ] += peso_pergunta


        acumuladores[
            criterio_id
        ][
            "quantidade"
        ] += 1


    # ========================================================
    # GERAR RESULTADO
    # ========================================================

    resultados = []


    for dados in acumuladores.values():

        if (
            dados[
                "soma_pesos"
            ]
            <= 0
        ):

            raise ValueError(
                "A soma dos pesos históricos das perguntas "
                "deve ser maior que zero para calcular "
                "o desempenho do critério."
            )


        media = (

            dados[
                "soma"
            ]

            /

            dados[
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


    # ========================================================
    # ORDENAR
    # ========================================================

    resultados.sort(
        key=lambda item: (

            item[
                "ordem_criterio"
            ]

            if (
                item[
                    "ordem_criterio"
                ]
                is not None
            )

            else 999999,

            item[
                "criterio_id"
            ]

        )
    )


    return resultados


# ============================================================
# CLASSIFICAR DESEMPENHO
# ============================================================

def classificar_desempenho(
    pontuacao: float
) -> str:
    """
    Classifica a pontuação final utilizando
    a escala definida pelo sistema.

    0 até < 5:
        Necessita desenvolvimento

    5 até < 7:
        Regular

    7 até < 8.5:
        Bom

    8.5 até 10:
        Muito bom
    """

    pontuacao = _validar_nota(

        pontuacao,

        "Pontuação"

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
# IDENTIFICAR DESTAQUES
# ============================================================

def identificar_destaques(
    desempenho_criterios: list[dict]
) -> dict:
    """
    Identifica:

    - critério com melhor desempenho;
    - critério com menor desempenho.
    """

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
# ATUALIZAR RESULTADO DA ENTREVISTA
# ============================================================

def atualizar_resultado_entrevista(
    entrevista_id: int,
    pontuacao_final: float
) -> None:
    """
    Registra a pontuação final e altera
    o status da entrevista para:

        avaliada
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    pontuacao_final = _validar_nota(

        pontuacao_final,

        "Pontuação final"

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


        if cursor.rowcount != 1:

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
    """
    Executa o Motor de Pontuação completo.

    Fluxo:

    1. verifica a entrevista;
    2. verifica seu status;
    3. confirma que todas as respostas existentes
       possuem avaliação;
    4. recalcula as pontuações das respostas;
    5. calcula a pontuação geral;
    6. calcula o desempenho por critério;
    7. classifica o desempenho;
    8. identifica destaques;
    9. atualiza a pontuação final;
    10. altera o status para avaliada;
    11. retorna o resultado consolidado.

    Todos os cálculos utilizam dados históricos.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    # ========================================================
    # BUSCAR ENTREVISTA
    # ========================================================

    entrevista = buscar_entrevista(
        entrevista_id
    )


    if entrevista is None:

        raise ValueError(
            "Entrevista não encontrada."
        )


    # ========================================================
    # VALIDAR STATUS
    # ========================================================

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


    # ========================================================
    # VERIFICAR SE TODAS AS RESPOSTAS FORAM AVALIADAS
    # ========================================================

    if not entrevista_totalmente_avaliada(
        entrevista_id
    ):

        raise ValueError(
            "Nem todas as respostas da entrevista "
            "foram avaliadas."
        )


    # ========================================================
    # RECALCULAR PONTUAÇÕES DAS RESPOSTAS
    # ========================================================

    atualizar_pontuacoes_respostas(
        entrevista_id
    )


    # ========================================================
    # CALCULAR PONTUAÇÃO FINAL
    # ========================================================

    pontuacao_final = (
        calcular_pontuacao_geral(
            entrevista_id
        )
    )


    # ========================================================
    # CALCULAR DESEMPENHO DOS CRITÉRIOS
    # ========================================================

    desempenho_criterios = (
        calcular_desempenho_criterios(
            entrevista_id
        )
    )


    # ========================================================
    # CLASSIFICAR
    # ========================================================

    classificacao = (
        classificar_desempenho(
            pontuacao_final
        )
    )


    # ========================================================
    # IDENTIFICAR DESTAQUES
    # ========================================================

    destaques = (
        identificar_destaques(
            desempenho_criterios
        )
    )


    # ========================================================
    # ATUALIZAR ENTREVISTA
    # ========================================================

    atualizar_resultado_entrevista(
        entrevista_id,
        pontuacao_final
    )


    # ========================================================
    # RETORNO
    # ========================================================

    return {

        "entrevista_id":
            entrevista_id,

        "tipo_entrevista":
            entrevista[
                "tipo_entrevista"
            ],

        "area_tecnica":
            entrevista[
                "area_tecnica"
            ],

        "subarea_tecnica":
            entrevista[
                "subarea_tecnica"
            ],

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