"""
analise.py

Módulo responsável pela análise das respostas utilizando
a API da OpenAI ou o modo MOCK durante o desenvolvimento.

Versão: 0.7

Responsabilidades:

- recuperar perguntas e respostas do banco;
- recuperar critérios de avaliação;
- construir as instruções para a OpenAI;
- permitir execução simulada através de MOCK_OPENAI;
- enviar respostas para a OpenAI Responses API;
- receber o resultado da análise;
- validar o JSON retornado;
- armazenar avaliações;
- armazenar notas por critério;
- controlar o status da entrevista;
- tratar falhas da API;
- impedir avaliações parciais de uma entrevista;
- permitir nova tentativa segura após erro de análise;
- impedir duas análises simultâneas da mesma entrevista.

INTEGRIDADE HISTÓRICA:

Os dados da pergunta utilizados na análise são recuperados
do snapshot armazenado em respostas.

O tipo de entrevista também é recuperado do snapshot
armazenado em entrevistas.

Assim, alterações administrativas posteriores não
modificam o contexto histórico da análise.

CONSISTÊNCIA TRANSACIONAL:

Cada resposta é persistida individualmente para evitar
manter uma transação SQLite aberta durante chamadas
externas de Inteligência Artificial.

A entrevista, entretanto, é tratada como uma única
unidade lógica.

Se qualquer resposta falhar:

- todas as avaliações da entrevista são removidas;
- as notas por critério são removidas por ON DELETE CASCADE;
- o status passa para erro_analise;
- uma nova tentativa pode começar limpa.

CONTROLE DE CONCORRÊNCIA:

A aquisição da entrevista para análise é realizada
atomicamente com BEGIN IMMEDIATE.

Somente uma requisição pode alterar uma entrevista de:

    finalizada
    erro_analise

para:

    em_analise

As demais requisições são rejeitadas antes de iniciar
o processamento.
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
# MOCK
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
# CLIENTE OPENAI
# ============================================================

def criar_cliente_openai() -> OpenAI:
    """
    Cria o cliente da OpenAI.
    """

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "A variável OPENAI_API_KEY não foi configurada."
        )

    return OpenAI(
        api_key=api_key
    )


# ============================================================
# BUSCAR CRITÉRIOS ATIVOS
# ============================================================

def buscar_criterios_ativos() -> list[dict]:
    """
    Recupera os critérios administrativos
    atualmente ativos.

    Esses critérios são utilizados somente
    em novas avaliações.
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
                    registro["id"],

                "nome":
                    registro["nome"],

                "descricao":
                    registro["descricao"],

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
# BUSCAR DADOS DA RESPOSTA
# ============================================================

def buscar_dados_resposta(
    resposta_id: int
) -> dict | None:
    """
    Recupera todos os dados necessários
    para analisar uma resposta.

    Os dados da pergunta e do tipo de entrevista
    são obtidos exclusivamente dos snapshots
    históricos.
    """

    if resposta_id <= 0:

        raise ValueError(
            "O ID da resposta é inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()

    try:

        cursor.execute(
            """
            SELECT

                r.id AS resposta_id,

                r.entrevista_id,

                r.texto_resposta,

                r.pergunta_id,

                r.pergunta_texto_aplicado
                    AS pergunta,

                r.exemplo_esperado_aplicado
                    AS exemplo_esperado,

                r.usa_star_aplicado
                    AS usa_star,

                r.competencia_id_aplicada
                    AS competencia_id,

                r.competencia_nome_aplicada
                    AS competencia,

                e.tipo_entrevista_id,

                e.tipo_entrevista_nome_aplicado
                    AS tipo_entrevista,

                e.tipo_entrevista_descricao_aplicada
                    AS tipo_entrevista_descricao

            FROM respostas r

            INNER JOIN entrevistas e
                ON e.id = r.entrevista_id

            WHERE r.id = ?
            """,
            (
                resposta_id,
            )
        )

        registro = cursor.fetchone()

        if registro is None:

            return None


        if (
            registro["pergunta"] is None

            or registro[
                "competencia_id"
            ] is None

            or registro[
                "competencia"
            ] is None

            or registro[
                "usa_star"
            ] is None

            or registro[
                "tipo_entrevista"
            ] is None
        ):

            raise ValueError(
                "A resposta não possui snapshot "
                "histórico completo."
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

            "resposta":
                registro[
                    "texto_resposta"
                ],

            "exemplo_esperado":
                registro[
                    "exemplo_esperado"
                ],

            "usa_star":
                bool(
                    registro[
                        "usa_star"
                    ]
                ),

            "competencia_id":
                registro[
                    "competencia_id"
                ],

            "competencia":
                registro[
                    "competencia"
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
    Constrói a descrição dos critérios.
    """

    linhas = []

    for criterio in criterios:

        linhas.append(
            f"- {criterio['nome']}: "
            f"{criterio['descricao']}"
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
    Constrói o prompt utilizado na avaliação.
    """

    rubrica = construir_rubrica(
        criterios
    )


    star = ""

    if dados["usa_star"]:

        star = """
Esta pergunta permite avaliação pelo método STAR.

Quando aplicável, considere:

SITUAÇÃO:
O candidato apresentou o contexto?

TAREFA:
Explicou sua responsabilidade ou problema?

AÇÃO:
Explicou o que efetivamente realizou?

RESULTADO:
Apresentou o resultado ou consequência?

O método STAR é complementar.

Não reduza automaticamente a avaliação apenas porque
a resposta não utiliza explicitamente os termos
Situação, Tarefa, Ação e Resultado.
"""


    exemplo = ""

    if dados["exemplo_esperado"]:

        exemplo = f"""
REFERÊNCIA INTERNA:

{dados["exemplo_esperado"]}

A referência acima serve apenas como apoio.

Não exija que o estudante utilize as mesmas palavras
ou exatamente a mesma estrutura.
"""


    return f"""
Você é um avaliador educacional de respostas de
entrevistas de emprego simuladas.

A finalidade desta avaliação é ajudar estudantes
universitários a desenvolver habilidades para
entrevistas profissionais.

Não realize decisões de contratação.

Não determine se o candidato deveria ser contratado
ou rejeitado.

Não avalie características pessoais do estudante.

Avalie exclusivamente o conteúdo textual fornecido.


TIPO DE ENTREVISTA:

{dados["tipo_entrevista"]}


COMPETÊNCIA:

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

Não invente experiências ou informações.

Não presuma informações ausentes.

Fundamente a avaliação exclusivamente no texto fornecido.

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
# CONSTRUIR SCHEMA
# ============================================================

def construir_schema(
    criterios: list[dict]
) -> dict:
    """
    Cria dinamicamente o JSON Schema.
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
# MOCK
# ============================================================

def gerar_resultado_mock(
    criterios: list[dict]
) -> dict:
    """
    Gera avaliação simulada local.
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
            indice % len(
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
    Executa análise real ou mock.
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
    Valida localmente o resultado.
    """

    if not isinstance(
        resultado,
        dict
    ):

        raise ValueError(
            "Resultado da análise inválido."
        )


    if "criterios" not in resultado:

        raise ValueError(
            "Critérios não encontrados "
            "no resultado."
        )


    avaliacoes = resultado[
        "criterios"
    ]


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


        try:

            nota = float(
                dados["nota"]
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ):

            raise ValueError(
                f"Nota inválida para o critério "
                f"{nome}."
            )


        if (
            nota < NOTA_MINIMA
            or nota > NOTA_MAXIMA
        ):

            raise ValueError(
                f"A nota de {nome} deve estar "
                "entre 0 e 10."
            )


        dados[
            "nota"
        ] = nota


        if not isinstance(
            dados.get(
                "observacao"
            ),
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

        if not isinstance(
            resultado.get(
                campo
            ),
            list
        ):

            raise ValueError(
                f"O campo {campo} deve ser uma lista."
            )


        if not all(
            isinstance(
                item,
                str
            )
            for item in resultado[
                campo
            ]
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
    Calcula a pontuação da resposta.
    """

    soma_pesos = sum(
        criterio[
            "peso"
        ]
        for criterio in criterios
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
            * peso
        )


    pontuacao /= (
        soma_pesos
    )


    return round(
        pontuacao,
        2
    )


# ============================================================
# MODELO UTILIZADO
# ============================================================

def obter_nome_modelo_avaliacao() -> str:
    """
    Retorna o identificador do modelo utilizado.
    """

    if MOCK_OPENAI:

        return "MOCK_OPENAI"

    return MODELO_OPENAI


# ============================================================
# SALVAR AVALIAÇÃO
# ============================================================

def salvar_avaliacao(
    resposta_id: int,
    resultado: dict,
    criterios: list[dict]
) -> int:
    """
    Armazena a avaliação de uma resposta.

    Os snapshots dos critérios são preenchidos
    automaticamente pelos triggers do banco.

    A função grava uma resposta por vez.

    A consistência da entrevista completa é
    responsabilidade de analisar_entrevista().
    """

    pontuacao = calcular_pontuacao_resposta(
        resultado,
        criterios
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT id

            FROM avaliacoes

            WHERE resposta_id = ?
            """,
            (
                resposta_id,
            )
        )


        if cursor.fetchone() is not None:

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

            VALUES (?, ?, ?, ?, ?, ?)
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


        avaliacao_id = (
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

                    observacao

                )

                VALUES (?, ?, ?, ?)
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
                    ]
                )
            )


        conexao.commit()


        return avaliacao_id


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# ANALISAR RESPOSTA
# ============================================================

def analisar_resposta(
    resposta_id: int
) -> int:
    """
    Executa o fluxo de análise de uma resposta.
    """

    dados = buscar_dados_resposta(
        resposta_id
    )


    if dados is None:

        raise ValueError(
            "Resposta não encontrada."
        )


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
    Retorna os IDs das respostas da entrevista
    utilizando a ordem histórica.
    """

    if entrevista_id <= 0:

        raise ValueError(
            "O ID da entrevista é inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT r.id

            FROM respostas r

            WHERE r.entrevista_id = ?

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
# REMOVER AVALIAÇÕES DA ENTREVISTA
# ============================================================

def _limpar_avaliacoes_entrevista(
    entrevista_id: int
) -> None:
    """
    Remove todas as avaliações pertencentes
    às respostas de uma entrevista.

    Os registros de avaliacao_criterios são
    removidos automaticamente através de
    ON DELETE CASCADE.

    Esta função somente deve ser utilizada pela
    requisição que adquiriu o direito de processar
    a entrevista.
    """

    if entrevista_id <= 0:

        raise ValueError(
            "O ID da entrevista é inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

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


        conexao.commit()


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# ALTERAR STATUS
# ============================================================

def _alterar_status(
    entrevista_id: int,
    status: str
) -> None:
    """
    Altera o status da entrevista.
    """

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
                status,
                entrevista_id
            )
        )


        conexao.commit()


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# ADQUIRIR ENTREVISTA PARA ANÁLISE
# ============================================================

def _adquirir_entrevista_para_analise(
    entrevista_id: int
) -> str:
    """
    Adquire atomicamente uma entrevista para análise.

    Esta é a principal proteção contra concorrência.

    O SQLite executa BEGIN IMMEDIATE, adquirindo
    imediatamente o bloqueio de escrita necessário.

    Dentro da mesma transação:

    1. a entrevista é localizada;
    2. seu status é validado;
    3. o status é alterado para em_analise;
    4. eventuais avaliações parciais de uma tentativa
       anterior são removidas;
    5. a transação é confirmada.

    Enquanto esta pequena transação estiver ativa,
    outra requisição não consegue executar outra
    alteração concorrente no banco.

    Depois do commit, uma segunda requisição encontrará
    a entrevista com status em_analise e será recusada.

    Retorna o status que existia antes da aquisição.
    """

    if entrevista_id <= 0:

        raise ValueError(
            "O ID da entrevista é inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ----------------------------------------------------
        # BEGIN IMMEDIATE
        #
        # Impede que duas requisições façam a transição
        # de estado simultaneamente.
        # ----------------------------------------------------

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        # ----------------------------------------------------
        # BUSCAR STATUS ATUAL
        # ----------------------------------------------------

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


        status_anterior = (
            entrevista[
                "status"
            ]
        )


        # ----------------------------------------------------
        # VALIDAR ESTADO
        # ----------------------------------------------------

        if status_anterior == "em_analise":

            raise ValueError(
                "A entrevista já está em análise."
            )


        if status_anterior == "avaliada":

            raise ValueError(
                "A entrevista já foi avaliada."
            )


        if status_anterior not in (
            "finalizada",
            "erro_analise"
        ):

            raise ValueError(
                "A entrevista precisa estar finalizada "
                "antes da análise."
            )


        # ----------------------------------------------------
        # TRANSIÇÃO ATÔMICA
        #
        # Mesmo após a leitura acima, utilizamos novamente
        # o status na cláusula WHERE.
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE entrevistas

            SET status = 'em_analise'

            WHERE id = ?

              AND status IN (
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
                "A entrevista já está sendo processada."
            )


        # ----------------------------------------------------
        # LIMPEZA DE TENTATIVA ANTERIOR
        #
        # Somente a requisição que conseguiu adquirir
        # a entrevista executa esta limpeza.
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # COMMIT DA AQUISIÇÃO
        # ----------------------------------------------------

        conexao.commit()


        return status_anterior


    except (
        sqlite3.Error,
        ValueError
    ):

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
    Analisa todas as respostas de uma entrevista.

    O primeiro passo é adquirir atomicamente
    o direito de processar a entrevista.

    Somente depois da aquisição são realizadas
    as chamadas de Inteligência Artificial.

    Isso impede duas requisições concorrentes de
    processarem a mesma entrevista ao mesmo tempo.

    Se ocorrer uma falha após a aquisição:

    - todas as avaliações desta tentativa são removidas;
    - notas de critérios são removidas por cascade;
    - status recebe erro_analise;
    - uma nova tentativa poderá ser executada.

    Importante:

    Caso _adquirir_entrevista_para_analise()
    rejeite a requisição, nenhuma limpeza é realizada.

    Isso impede que uma segunda requisição concorrente
    apague o trabalho da primeira.
    """

    if entrevista_id <= 0:

        raise ValueError(
            "O ID da entrevista é inválido."
        )


    # ========================================================
    # AQUISIÇÃO ATÔMICA
    #
    # Se outra requisição já estiver processando,
    # a exceção ocorre aqui.
    #
    # Neste caso NÃO entramos no bloco de rollback
    # compensatório abaixo.
    # ========================================================

    _adquirir_entrevista_para_analise(
        entrevista_id
    )


    # ========================================================
    # A PARTIR DESTE PONTO ESTA REQUISIÇÃO É A DONA
    # DO PROCESSAMENTO DA ENTREVISTA.
    # ========================================================

    try:

        # ----------------------------------------------------
        # BUSCAR RESPOSTAS
        # ----------------------------------------------------

        respostas = (
            buscar_respostas_entrevista(
                entrevista_id
            )
        )


        if not respostas:

            raise ValueError(
                "A entrevista não possui respostas."
            )


        # ----------------------------------------------------
        # ANALISAR RESPOSTAS
        # ----------------------------------------------------

        avaliacoes = []


        for resposta_id in respostas:

            avaliacao_id = (
                analisar_resposta(
                    resposta_id
                )
            )


            avaliacoes.append(
                avaliacao_id
            )


        # ----------------------------------------------------
        # PROCESSAR RESULTADO FINAL
        # ----------------------------------------------------

        resultado_final = (
            processar_avaliacao(
                entrevista_id
            )
        )


        # ----------------------------------------------------
        # SUCESSO
        # ----------------------------------------------------

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

            "avaliacoes":
                avaliacoes,

            "resultado_final":
                resultado_final

        }


    except Exception:

        # ----------------------------------------------------
        # ROLLBACK COMPENSATÓRIO
        #
        # Somente esta requisição chegou até aqui após
        # adquirir a entrevista.
        #
        # Por isso ela pode remover seus próprios
        # resultados parciais com segurança.
        # ----------------------------------------------------

        try:

            _limpar_avaliacoes_entrevista(
                entrevista_id
            )

        finally:

            _alterar_status(
                entrevista_id,
                "erro_analise"
            )


        raise