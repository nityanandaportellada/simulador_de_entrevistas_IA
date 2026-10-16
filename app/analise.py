"""
analise.py

Módulo responsável pela análise das respostas utilizando
a API da OpenAI ou o modo MOCK durante o desenvolvimento.

Versão: 0.8

Responsabilidades:

- recuperar respostas utilizando snapshots históricos;
- recuperar o tipo de entrevista aplicado;
- recuperar área e subárea aplicadas;
- recuperar pergunta e competência históricas;
- recuperar critérios ativos de avaliação;
- congelar em memória os critérios utilizados por uma entrevista;
- construir as instruções de avaliação;
- acrescentar contexto técnico de área/subárea;
- permitir execução simulada através de MOCK_OPENAI;
- enviar respostas para a OpenAI Responses API;
- validar o resultado retornado;
- armazenar avaliações;
- armazenar notas por critério;
- preservar os pesos e dados históricos dos critérios;
- controlar o status da entrevista;
- impedir análise concorrente da mesma entrevista;
- limpar avaliações parciais caso ocorra falha;
- executar o Motor de Pontuação.

IMPORTANTE:

O sistema continua utilizando MOCK_OPENAI=true
durante a fase atual de desenvolvimento.

Quando MOCK_OPENAI=true:

- nenhuma chamada externa é realizada;
- não é necessária OPENAI_API_KEY;
- o restante do fluxo funciona normalmente.

A integração real será validada posteriormente.

INTEGRIDADE HISTÓRICA:

A análise utiliza os snapshots gravados nas respostas
e na entrevista.

Além disso, os critérios ativos são carregados
UMA ÚNICA VEZ no início da análise da entrevista.

Isso garante que todas as respostas da mesma entrevista
sejam avaliadas utilizando exatamente o mesmo conjunto
de critérios, mesmo que um administrador altere os
cadastros enquanto a análise estiver sendo processada.

Alterações posteriores em:

- pergunta;
- competência;
- tipo de entrevista;
- área;
- subárea;
- critérios;
- pesos dos critérios;

não modificam avaliações históricas.
"""

import json
import os
import sqlite3

from typing import Any


from openai import OpenAI


try:

    from .database import conectar_banco

    from .avaliacao import (
        processar_avaliacao
    )


except ImportError:

    from database import conectar_banco

    from avaliacao import (
        processar_avaliacao
    )


# ============================================================
# CONFIGURAÇÕES
# ============================================================

MODELO_OPENAI = os.getenv(
    "OPENAI_MODEL",
    "gpt-6-luna"
)


NOTA_MINIMA = 0.0

NOTA_MAXIMA = 10.0


# ============================================================
# MODO MOCK
# ============================================================

MOCK_OPENAI = (

    os.getenv(
        "MOCK_OPENAI",
        "false"
    )
    .strip()
    .lower()

    in (

        "1",

        "true",

        "yes",

        "sim"

    )

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
# CLIENTE OPENAI
# ============================================================

def criar_cliente_openai() -> OpenAI:
    """
    Cria o cliente utilizado para comunicação
    com a API da OpenAI.

    Esta função somente é executada quando
    MOCK_OPENAI estiver desativado.
    """

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )


    if not api_key:

        raise RuntimeError(
            "A variável OPENAI_API_KEY "
            "não foi configurada."
        )


    return OpenAI(
        api_key=api_key
    )


# ============================================================
# NOME DO MODELO
# ============================================================

def obter_nome_modelo_avaliacao() -> str:
    """
    Retorna o nome armazenado na avaliação.
    """

    if MOCK_OPENAI:

        return "MOCK_OPENAI"


    return MODELO_OPENAI


# ============================================================
# BUSCAR CRITÉRIOS ATIVOS
# ============================================================

def buscar_criterios_ativos() -> list[dict]:
    """
    Recupera os critérios atualmente ativos.

    Na análise de uma entrevista esta função
    será chamada uma única vez.

    O resultado será reutilizado em todas as
    respostas da mesma entrevista.
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


        criterios = []


        for registro in registros:

            peso = registro[
                "peso"
            ]


            if peso is None:

                raise ValueError(
                    "Existe critério ativo sem peso definido."
                )


            if float(
                peso
            ) < 0:

                raise ValueError(
                    "Existe critério ativo com peso negativo."
                )


            criterios.append(
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
                        float(
                            peso
                        ),

                    "ordem":
                        registro[
                            "ordem"
                        ]

                }
            )


        return criterios


    finally:

        conexao.close()


# ============================================================
# BUSCAR DADOS HISTÓRICOS DA RESPOSTA
# ============================================================

def buscar_dados_resposta(
    resposta_id: int
) -> dict | None:
    """
    Recupera todos os dados necessários
    para avaliar uma resposta.

    IMPORTANTE:

    A função NÃO consulta o texto atual da
    tabela perguntas.

    Também não utiliza o nome atual do tipo,
    competência, área ou subárea.

    São utilizados os snapshots históricos
    gravados na entrevista e na resposta.
    """

    _validar_id(
        resposta_id,
        "ID da resposta"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT

                r.id
                    AS resposta_id,

                r.entrevista_id,

                r.pergunta_id,

                r.texto_resposta,

                r.tempo_resposta,

                r.data_resposta,


                r.pergunta_texto_aplicado
                    AS pergunta,

                r.exemplo_esperado_aplicado
                    AS exemplo_esperado,

                r.competencia_id_aplicada
                    AS competencia_id,

                r.competencia_nome_aplicada
                    AS competencia,

                r.peso_pergunta_aplicado
                    AS peso_pergunta,

                r.usa_star_aplicado
                    AS usa_star,

                r.ordem_pergunta_aplicada
                    AS ordem_pergunta,


                e.tipo_entrevista_id,

                e.tipo_entrevista_nome_aplicado
                    AS tipo_entrevista,

                e.tipo_entrevista_descricao_aplicada
                    AS tipo_entrevista_descricao,


                e.area_tecnica_id,

                e.area_tecnica_nome_aplicado
                    AS area_tecnica,


                e.subarea_tecnica_id,

                e.subarea_tecnica_nome_aplicado
                    AS subarea_tecnica

            FROM respostas r

            INNER JOIN entrevistas e

                ON e.id =
                    r.entrevista_id

            WHERE r.id = ?
            """,
            (
                resposta_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        # ====================================================
        # VALIDAR SNAPSHOT DA PERGUNTA
        # ====================================================

        if (
            registro[
                "pergunta"
            ]
            is None
        ):

            raise ValueError(
                "A resposta não possui o snapshot "
                "histórico da pergunta."
            )


        if (
            registro[
                "competencia_id"
            ]
            is None
        ):

            raise ValueError(
                "A resposta não possui o snapshot "
                "histórico da competência."
            )


        if (
            registro[
                "competencia"
            ]
            is None
        ):

            raise ValueError(
                "A resposta não possui o nome histórico "
                "da competência."
            )


        if (
            registro[
                "peso_pergunta"
            ]
            is None
        ):

            raise ValueError(
                "A resposta não possui o peso histórico "
                "da pergunta."
            )


        if (
            registro[
                "usa_star"
            ]
            is None
        ):

            raise ValueError(
                "A resposta não possui a configuração "
                "histórica do método STAR."
            )


        # ====================================================
        # VALIDAR TIPO HISTÓRICO
        # ====================================================

        if (
            registro[
                "tipo_entrevista"
            ]
            is None
        ):

            raise ValueError(
                "A entrevista não possui o snapshot "
                "histórico do tipo de entrevista."
            )


        return {

            "resposta_id":
                registro[
                    "resposta_id"
                ],

            "entrevista_id":
                registro[
                    "entrevista_id"
                ],

            "pergunta_id":
                registro[
                    "pergunta_id"
                ],

            "pergunta":
                registro[
                    "pergunta"
                ],

            "exemplo_esperado":
                registro[
                    "exemplo_esperado"
                ],

            "competencia_id":
                registro[
                    "competencia_id"
                ],

            "competencia":
                registro[
                    "competencia"
                ],

            "peso_pergunta":
                registro[
                    "peso_pergunta"
                ],

            "usa_star":
                bool(
                    registro[
                        "usa_star"
                    ]
                ),

            "ordem_pergunta":
                registro[
                    "ordem_pergunta"
                ],

            "resposta":
                registro[
                    "texto_resposta"
                ],

            "tempo_resposta":
                registro[
                    "tempo_resposta"
                ],

            "data_resposta":
                registro[
                    "data_resposta"
                ],

            "tipo_entrevista_id":
                registro[
                    "tipo_entrevista_id"
                ],

            "tipo_entrevista":
                registro[
                    "tipo_entrevista"
                ],

            "tipo_entrevista_descricao":
                registro[
                    "tipo_entrevista_descricao"
                ],

            "area_tecnica_id":
                registro[
                    "area_tecnica_id"
                ],

            "area_tecnica":
                registro[
                    "area_tecnica"
                ],

            "subarea_tecnica_id":
                registro[
                    "subarea_tecnica_id"
                ],

            "subarea_tecnica":
                registro[
                    "subarea_tecnica"
                ]

        }


    finally:

        conexao.close()


# ============================================================
# CONSTRUIR RUBRICA
# ============================================================

def construir_rubrica(
    criterios: list[dict]
) -> str:
    """
    Constrói a descrição textual dos critérios
    utilizados pela entrevista.
    """

    linhas = []


    for criterio in criterios:

        descricao = (
            criterio[
                "descricao"
            ]
            or
            "Sem descrição adicional."
        )


        linhas.append(

            (
                f"- {criterio['nome']}: "
                f"{descricao}"
            )

        )


    return "\n".join(
        linhas
    )


# ============================================================
# CONSTRUIR PROMPT
# ============================================================

def construir_prompt(
    dados: dict,
    criterios: list[dict]
) -> str:
    """
    Constrói o conteúdo utilizado para avaliar
    uma resposta.

    Para entrevistas técnicas, são incluídos:

    - área;
    - subárea.
    """

    rubrica = construir_rubrica(
        criterios
    )


    # ========================================================
    # CONTEXTO DA ENTREVISTA
    # ========================================================

    linhas_contexto = [

        (
            "TIPO DE ENTREVISTA:\n"
            f"{dados['tipo_entrevista']}"
        )

    ]


    if dados.get(
        "area_tecnica"
    ):

        linhas_contexto.append(

            (
                "ÁREA TÉCNICA:\n"
                f"{dados['area_tecnica']}"
            )

        )


    if dados.get(
        "subarea_tecnica"
    ):

        linhas_contexto.append(

            (
                "SUBÁREA TÉCNICA:\n"
                f"{dados['subarea_tecnica']}"
            )

        )


    contexto = "\n\n".join(
        linhas_contexto
    )


    # ========================================================
    # MÉTODO STAR
    # ========================================================

    if dados[
        "usa_star"
    ]:

        star = """
A pergunta foi cadastrada com utilização do método STAR.

Ao avaliar, considere se a resposta apresenta,
quando aplicável:

- Situação;
- Tarefa;
- Ação;
- Resultado.

Não penalize de maneira mecânica a ausência dos
nomes dessas etapas. Avalie se os elementos estão
presentes no conteúdo da resposta.
""".strip()


    else:

        star = """
A pergunta não exige obrigatoriamente a utilização
do método STAR.
""".strip()


    # ========================================================
    # EXEMPLO ESPERADO
    # ========================================================

    if dados.get(
        "exemplo_esperado"
    ):

        exemplo = f"""
REFERÊNCIA DE RESPOSTA ESPERADA:

{dados["exemplo_esperado"]}

A referência serve apenas como apoio de avaliação.

Não exija reprodução literal e não considere
apenas respostas idênticas à referência como corretas.
""".strip()


    else:

        exemplo = """
Não existe exemplo de resposta esperado cadastrado
para esta pergunta.
""".strip()


    return f"""
Você está avaliando a resposta de um estudante em um
simulador educacional de entrevistas profissionais.

O objetivo é fornecer uma avaliação construtiva,
objetiva e útil para o desenvolvimento profissional.

{contexto}


COMPETÊNCIA AVALIADA:

{dados["competencia"]}


PERGUNTA:

{dados["pergunta"]}


RESPOSTA DO ESTUDANTE:

{dados["resposta"]}


CRITÉRIOS:

{rubrica}


ESCALA:

Utilize notas entre 0.0 e 10.0.

0.0 até 2.0
Muito insuficiente.

2.1 até 4.0
Insuficiente.

4.1 até 6.0
Parcialmente adequada.

6.1 até 8.0
Adequada, apresentando oportunidades de melhoria.

8.1 até 9.0
Muito adequada.

9.1 até 10.0
Excepcionalmente bem desenvolvida.


REGRAS IMPORTANTES:

Avalie cada critério separadamente.

Considere o tipo de entrevista informado.

Quando houver área e subárea técnica, utilize esse
contexto para interpretar adequadamente a pergunta
e a resposta.

Não invente experiências, conhecimentos ou
informações não presentes na resposta.

Não presuma informações ausentes.

Fundamente a avaliação exclusivamente no conteúdo
fornecido.

Produza observações curtas e objetivas.

O feedback deve possuir finalidade educacional.

{star}

{exemplo}

Produza:

- nota para cada critério;
- justificativa curta para cada nota;
- pontos fortes;
- pontos de melhoria;
- feedback geral.
""".strip()


# ============================================================
# CONSTRUIR JSON SCHEMA
# ============================================================

def construir_schema(
    criterios: list[dict]
) -> dict:
    """
    Cria dinamicamente o JSON Schema
    da avaliação.
    """

    propriedades_criterios = {}

    nomes_criterios = []


    for criterio in criterios:

        nome = criterio[
            "nome"
        ]


        nomes_criterios.append(
            nome
        )


        propriedades_criterios[
            nome
        ] = {

            "type":
                "object",

            "properties": {

                "nota": {

                    "type":
                        "number",

                    "minimum":
                        NOTA_MINIMA,

                    "maximum":
                        NOTA_MAXIMA

                },

                "observacao": {

                    "type":
                        "string"

                }

            },

            "required": [

                "nota",

                "observacao"

            ],

            "additionalProperties":
                False

        }


    return {

        "type":
            "object",

        "properties": {

            "criterios": {

                "type":
                    "object",

                "properties":
                    propriedades_criterios,

                "required":
                    nomes_criterios,

                "additionalProperties":
                    False

            },

            "pontos_fortes": {

                "type":
                    "array",

                "items": {

                    "type":
                        "string"

                }

            },

            "pontos_melhoria": {

                "type":
                    "array",

                "items": {

                    "type":
                        "string"

                }

            },

            "feedback": {

                "type":
                    "string"

            }

        },

        "required": [

            "criterios",

            "pontos_fortes",

            "pontos_melhoria",

            "feedback"

        ],

        "additionalProperties":
            False

    }


# ============================================================
# GERAR RESULTADO MOCK
# ============================================================

def gerar_resultado_mock(
    criterios: list[dict]
) -> dict:
    """
    Gera uma avaliação simulada.

    Mantém exatamente a mesma estrutura
    utilizada pelo modo real.
    """

    criterios_mock = {}


    notas_mock = [

        8.0,

        7.5,

        8.5,

        7.0,

        9.0

    ]


    for indice, criterio in enumerate(
        criterios
    ):

        nome = criterio[
            "nome"
        ]


        nota = notas_mock[

            indice
            %
            len(
                notas_mock
            )

        ]


        criterios_mock[
            nome
        ] = {

            "nota":
                nota,

            "observacao":
                (
                    "Avaliação simulada pelo modo "
                    "MOCK_OPENAI para o critério "
                    f"{nome}."
                )

        }


    return {

        "criterios":
            criterios_mock,

        "pontos_fortes": [

            (
                "A resposta apresenta conteúdo "
                "relacionado à pergunta."
            ),

            (
                "A resposta possui estrutura "
                "compreensível."
            )

        ],

        "pontos_melhoria": [

            (
                "A resposta pode apresentar exemplos "
                "mais específicos."
            ),

            (
                "Os resultados das ações podem ser "
                "descritos com maior detalhamento."
            )

        ],

        "feedback":
            (
                "Avaliação simulada para fins de teste. "
                "A resposta apresenta estrutura adequada "
                "e relação com a pergunta. Para melhorar, "
                "podem ser utilizados exemplos mais "
                "concretos, com maior detalhamento das "
                "ações realizadas e dos resultados "
                "alcançados. Este feedback foi produzido "
                "pelo modo MOCK_OPENAI e não representa "
                "uma avaliação realizada pela OpenAI."
            )

    }


# ============================================================
# CHAMAR OPENAI
# ============================================================

def chamar_openai(
    prompt: str,
    criterios: list[dict]
) -> dict:
    """
    Executa a análise.

    MOCK_OPENAI=true:
        retorna avaliação simulada.

    MOCK_OPENAI=false:
        utiliza a OpenAI Responses API.
    """

    if MOCK_OPENAI:

        print(
            "[MOCK_OPENAI] "
            "Gerando avaliação simulada. "
            "Nenhuma chamada externa será realizada."
        )


        return gerar_resultado_mock(
            criterios
        )


    cliente = criar_cliente_openai()


    schema = construir_schema(
        criterios
    )


    resposta = cliente.responses.create(

        model=MODELO_OPENAI,

        instructions=(
            "Você é um avaliador educacional "
            "especializado em entrevistas profissionais. "
            "Siga rigorosamente os critérios fornecidos "
            "e produza somente a estrutura solicitada."
        ),

        input=prompt,

        text={

            "format": {

                "type":
                    "json_schema",

                "name":
                    "avaliacao_entrevista",

                "strict":
                    True,

                "schema":
                    schema

            }

        }

    )


    texto = resposta.output_text


    if not texto:

        raise RuntimeError(
            "A OpenAI não retornou conteúdo "
            "para a análise."
        )


    try:

        resultado = json.loads(
            texto
        )


    except json.JSONDecodeError as erro:

        raise RuntimeError(
            "A resposta retornada pela OpenAI "
            "não contém JSON válido."
        ) from erro


    return resultado


# ============================================================
# VALIDAR RESULTADO
# ============================================================

def validar_resultado(
    resultado: Any,
    criterios: list[dict]
) -> dict:
    """
    Valida localmente o resultado da análise.
    """

    if not isinstance(
        resultado,
        dict
    ):

        raise ValueError(
            "Resultado da análise inválido."
        )


    if (
        "criterios"
        not in resultado
    ):

        raise ValueError(
            "Critérios não encontrados "
            "no resultado."
        )


    avaliacoes = resultado[
        "criterios"
    ]


    if not isinstance(
        avaliacoes,
        dict
    ):

        raise ValueError(
            "O campo criterios é inválido."
        )


    for criterio in criterios:

        nome = criterio[
            "nome"
        ]


        if nome not in avaliacoes:

            raise ValueError(
                f"Critério ausente: {nome}"
            )


        dados = avaliacoes[
            nome
        ]


        if not isinstance(
            dados,
            dict
        ):

            raise ValueError(
                f"A avaliação do critério "
                f"{nome} é inválida."
            )


        try:

            nota = float(
                dados[
                    "nota"
                ]
            )


        except (
            KeyError,
            TypeError,
            ValueError
        ) as erro:

            raise ValueError(
                f"Nota inválida para o critério "
                f"{nome}."
            ) from erro


        if (

            nota < NOTA_MINIMA

            or

            nota > NOTA_MAXIMA

        ):

            raise ValueError(
                f"A nota de {nome} deve estar "
                "entre 0 e 10."
            )


        dados[
            "nota"
        ] = nota


        observacao = dados.get(
            "observacao"
        )


        if not isinstance(
            observacao,
            str
        ):

            raise ValueError(
                f"Observação inválida para "
                f"{nome}."
            )


    for campo in (

        "pontos_fortes",

        "pontos_melhoria"

    ):

        valor = resultado.get(
            campo
        )


        if not isinstance(
            valor,
            list
        ):

            raise ValueError(
                f"O campo {campo} deve "
                "ser uma lista."
            )


        if not all(

            isinstance(
                item,
                str
            )

            for item
            in valor

        ):

            raise ValueError(
                f"Todos os itens de {campo} "
                "devem ser textos."
            )


    if not isinstance(

        resultado.get(
            "feedback"
        ),

        str

    ):

        raise ValueError(
            "O feedback retornado é inválido."
        )


    return resultado


# ============================================================
# CALCULAR PONTUAÇÃO DA RESPOSTA
# ============================================================

def calcular_pontuacao_resposta(
    resultado: dict,
    criterios: list[dict]
) -> float:
    """
    Calcula a pontuação ponderada da resposta.
    """

    soma_pesos = sum(

        criterio[
            "peso"
        ]

        for criterio
        in criterios

    )


    if soma_pesos <= 0:

        raise ValueError(
            "A soma dos pesos deve ser "
            "maior que zero."
        )


    pontuacao = 0.0


    for criterio in criterios:

        nome = criterio[
            "nome"
        ]


        nota = resultado[
            "criterios"
        ][nome][
            "nota"
        ]


        peso = criterio[
            "peso"
        ]


        pontuacao += (
            nota
            *
            peso
        )


    pontuacao /= soma_pesos


    return round(
        pontuacao,
        2
    )


# ============================================================
# SALVAR AVALIAÇÃO
# ============================================================

def salvar_avaliacao(
    resposta_id: int,
    resultado: dict,
    criterios: list[dict]
) -> int:
    """
    Armazena uma avaliação.

    Também congela, para cada critério:

    - nome;
    - descrição;
    - peso;
    - ordem.
    """

    _validar_id(
        resposta_id,
        "ID da resposta"
    )


    pontuacao = calcular_pontuacao_resposta(

        resultado,

        criterios

    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        cursor.execute(
            """
            SELECT id

            FROM respostas

            WHERE id = ?
            """,
            (
                resposta_id,
            )
        )


        if cursor.fetchone() is None:

            raise ValueError(
                "Resposta não encontrada."
            )


        cursor.execute(
            """
            SELECT id

            FROM avaliacoes

            WHERE resposta_id = ?

            LIMIT 1
            """,
            (
                resposta_id,
            )
        )


        if (
            cursor.fetchone()
            is not None
        ):

            raise ValueError(
                "Esta resposta já possui avaliação."
            )


        pontos_fortes = json.dumps(

            resultado[
                "pontos_fortes"
            ],

            ensure_ascii=False

        )


        pontos_melhoria = json.dumps(

            resultado[
                "pontos_melhoria"
            ],

            ensure_ascii=False

        )


        modelo_utilizado = (
            obter_nome_modelo_avaliacao()
        )


        cursor.execute(
            """
            INSERT INTO avaliacoes (

                resposta_id,

                pontuacao,

                pontos_fortes,

                pontos_melhoria,

                feedback,

                modelo_ia

            )

            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (

                resposta_id,

                pontuacao,

                pontos_fortes,

                pontos_melhoria,

                resultado[
                    "feedback"
                ],

                modelo_utilizado

            )
        )


        avaliacao_id = int(
            cursor.lastrowid
        )


        for criterio in criterios:

            nome = criterio[
                "nome"
            ]


            dados = resultado[
                "criterios"
            ][nome]


            cursor.execute(
                """
                INSERT INTO avaliacao_criterios (

                    avaliacao_id,

                    criterio_id,

                    nota,

                    observacao,

                    peso_aplicado,

                    criterio_nome_aplicado,

                    criterio_descricao_aplicada,

                    criterio_ordem_aplicada

                )

                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (

                    avaliacao_id,

                    criterio[
                        "id"
                    ],

                    dados[
                        "nota"
                    ],

                    dados[
                        "observacao"
                    ],

                    criterio[
                        "peso"
                    ],

                    criterio[
                        "nome"
                    ],

                    criterio[
                        "descricao"
                    ],

                    criterio[
                        "ordem"
                    ]

                )
            )


        conexao.commit()


        return avaliacao_id


    except sqlite3.IntegrityError as erro:

        conexao.rollback()


        mensagem = str(
            erro
        ).lower()


        if (
            "unique constraint failed"
            in mensagem
        ):

            raise ValueError(
                "Esta resposta já possui avaliação."
            ) from erro


        raise


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# ANALISAR UMA RESPOSTA
# ============================================================

def analisar_resposta(
    resposta_id: int,
    criterios: list[dict] | None = None
) -> int:
    """
    Executa o fluxo completo de avaliação
    de uma resposta.

    Quando criterios for informado, utiliza
    exatamente o conjunto recebido.

    Isso é utilizado por analisar_entrevista()
    para garantir que todas as respostas da mesma
    entrevista sejam analisadas com o mesmo conjunto
    de critérios.

    Quando chamada isoladamente, a função ainda pode
    buscar os critérios ativos automaticamente.
    """

    dados = buscar_dados_resposta(
        resposta_id
    )


    if dados is None:

        raise ValueError(
            "Resposta não encontrada."
        )


    if criterios is None:

        criterios = (
            buscar_criterios_ativos()
        )


    if not criterios:

        raise ValueError(
            "Nenhum critério ativo encontrado."
        )


    prompt = construir_prompt(

        dados,

        criterios

    )


    resultado = chamar_openai(

        prompt,

        criterios

    )


    resultado = validar_resultado(

        resultado,

        criterios

    )


    return salvar_avaliacao(

        resposta_id,

        resultado,

        criterios

    )


# ============================================================
# BUSCAR RESPOSTAS DA ENTREVISTA
# ============================================================

def buscar_respostas_entrevista(
    entrevista_id: int
) -> list[int]:
    """
    Retorna IDs das respostas da entrevista.

    A ordenação utiliza o snapshot histórico
    da ordem da pergunta.
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
                r.id

            FROM respostas r

            WHERE
                r.entrevista_id = ?

            ORDER BY

                COALESCE(
                    r.ordem_pergunta_aplicada,
                    999999
                ),

                r.id
            """,
            (
                entrevista_id,
            )
        )


        return [

            registro[
                "id"
            ]

            for registro
            in cursor.fetchall()

        ]


    finally:

        conexao.close()


# ============================================================
# ALTERAR STATUS
# ============================================================

def _alterar_status(
    entrevista_id: int,
    novo_status: str
) -> None:
    """
    Altera o status da entrevista.
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
            UPDATE entrevistas

            SET status = ?

            WHERE id = ?
            """,
            (
                novo_status,
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
# ADQUIRIR ENTREVISTA PARA ANÁLISE
# ============================================================

def _adquirir_entrevista_para_analise(
    entrevista_id: int
) -> None:
    """
    Reserva atomicamente uma entrevista
    para análise.

    Isso impede que duas requisições analisem
    simultaneamente a mesma entrevista.

    Status aceitos:

    - finalizada;
    - erro_analise.

    Em caso de nova tentativa após erro,
    avaliações parciais anteriores são removidas.
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
            BEGIN IMMEDIATE
            """
        )


        cursor.execute(
            """
            SELECT
                id,
                status

            FROM entrevistas

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )


        entrevista = cursor.fetchone()


        if entrevista is None:

            raise ValueError(
                "Entrevista não encontrada."
            )


        if entrevista[
            "status"
        ] not in (

            "finalizada",

            "erro_analise"

        ):

            raise ValueError(
                "A entrevista precisa estar finalizada "
                "antes da análise."
            )


        if (
            entrevista[
                "status"
            ]
            == "erro_analise"
        ):

            cursor.execute(
                """
                DELETE FROM avaliacoes

                WHERE resposta_id IN (

                    SELECT id

                    FROM respostas

                    WHERE entrevista_id = ?

                )
                """,
                (
                    entrevista_id,
                )
            )


            cursor.execute(
                """
                UPDATE entrevistas

                SET pontuacao_final = NULL

                WHERE id = ?
                """,
                (
                    entrevista_id,
                )
            )


        cursor.execute(
            """
            UPDATE entrevistas

            SET status = 'em_analise'

            WHERE
                id = ?

              AND
                status IN (
                    'finalizada',
                    'erro_analise'
                )
            """,
            (
                entrevista_id,
            )
        )


        if cursor.rowcount != 1:

            raise ValueError(
                "A entrevista já está sendo analisada "
                "ou não está disponível para análise."
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
# LIMPAR ANÁLISE PARCIAL
# ============================================================

def _limpar_analise_parcial(
    entrevista_id: int
) -> None:
    """
    Remove avaliações geradas parcialmente
    quando a análise da entrevista falha.

    Ao final:

    status = erro_analise
    pontuacao_final = NULL
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        cursor.execute(
            """
            DELETE FROM avaliacoes

            WHERE resposta_id IN (

                SELECT id

                FROM respostas

                WHERE entrevista_id = ?

            )
            """,
            (
                entrevista_id,
            )
        )


        cursor.execute(
            """
            UPDATE entrevistas

            SET

                status = 'erro_analise',

                pontuacao_final = NULL

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )


        conexao.commit()


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# ANALISAR ENTREVISTA
# ============================================================

def analisar_entrevista(
    entrevista_id: int
) -> dict:
    """
    Analisa todas as respostas pertencentes
    a uma entrevista finalizada.

    Fluxo:

    1. reserva atomicamente a entrevista;
    2. altera status para em_analise;
    3. recupera os critérios ativos UMA VEZ;
    4. congela esse conjunto em memória;
    5. recupera as respostas históricas;
    6. analisa todas as respostas utilizando
       exatamente os mesmos critérios;
    7. salva avaliações e snapshots dos critérios;
    8. executa o Motor de Pontuação;
    9. finaliza a entrevista como avaliada.

    Em caso de erro:

    - avaliações parciais são removidas;
    - pontuação final é limpa;
    - status passa para erro_analise.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    # ========================================================
    # RESERVAR ENTREVISTA
    # ========================================================

    _adquirir_entrevista_para_analise(
        entrevista_id
    )


    try:

        # ====================================================
        # CONGELAR CRITÉRIOS NA MEMÓRIA
        # ====================================================

        criterios = (
            buscar_criterios_ativos()
        )


        if not criterios:

            raise ValueError(
                "Nenhum critério ativo encontrado."
            )


        # ====================================================
        # RESPOSTAS
        # ====================================================

        respostas = buscar_respostas_entrevista(
            entrevista_id
        )


        if not respostas:

            raise ValueError(
                "A entrevista não possui respostas."
            )


        avaliacoes = []


        # ====================================================
        # ANALISAR TODAS COM O MESMO CONJUNTO
        # ====================================================

        for resposta_id in respostas:

            avaliacao_id = analisar_resposta(

                resposta_id,

                criterios=criterios

            )


            avaliacoes.append(
                avaliacao_id
            )


        # ====================================================
        # MOTOR DE PONTUAÇÃO
        # ====================================================

        resultado_final = processar_avaliacao(
            entrevista_id
        )


        # ====================================================
        # RETORNO
        # ====================================================

        return {

            "entrevista_id":
                entrevista_id,

            "modo_analise":
                (
                    "mock"
                    if MOCK_OPENAI
                    else "openai"
                ),

            "modelo":
                obter_nome_modelo_avaliacao(),

            "quantidade_criterios_aplicados":
                len(
                    criterios
                ),

            "avaliacoes":
                avaliacoes,

            "resultado_final":
                resultado_final

        }


    except Exception:

        _limpar_analise_parcial(
            entrevista_id
        )


        raise