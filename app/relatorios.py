"""
relatorios.py

Serviço responsável pela geração dos relatórios
do Simulador de Entrevistas.

Versão: 0.7

Responsabilidades:

- buscar os dados da entrevista;
- reunir perguntas e respostas;
- reunir avaliações realizadas pela IA;
- reunir notas por critério;
- apresentar a pontuação final;
- apresentar classificação;
- apresentar desempenho consolidado por critério;
- identificar melhor critério;
- identificar critério a desenvolver;
- organizar os dados utilizados pelo relatório.

IMPORTANTE:

Este módulo não possui rotas HTTP.

A exposição dos dados através da API é
responsabilidade de:

app/routers/relatorios.py

Este módulo também NÃO realiza nova análise
por Inteligência Artificial.

Ele utiliza somente dados já armazenados
no banco de dados.

INTEGRIDADE HISTÓRICA:

Os dados da pergunta apresentados no relatório são
obtidos do snapshot armazenado em respostas.

O relatório não consulta a versão administrativa
atual da pergunta para reconstruir entrevistas antigas.
"""

import json


from .entrevistas import (
    buscar_entrevista
)

from .respostas import (
    listar_respostas_entrevista,
    buscar_snapshot_resposta
)

from .avaliacao import (
    buscar_avaliacoes_entrevista,
    buscar_notas_criterios,
    calcular_desempenho_criterios,
    classificar_desempenho,
    identificar_destaques
)


# ============================================================
# FUNÇÃO AUXILIAR - OBTER VALOR
# ============================================================

def _valor(
    objeto,
    atributo,
    padrao=None
):
    """
    Obtém um valor independentemente de o objeto
    ser um dicionário ou um objeto Python.

    Isso facilita a integração entre os módulos
    existentes do sistema.
    """

    if objeto is None:

        return padrao


    if isinstance(
        objeto,
        dict
    ):

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
# FUNÇÃO AUXILIAR - CONVERTER JSON PARA LISTA
# ============================================================

def _converter_lista_json(
    valor
) -> list:
    """
    Converte campos armazenados como JSON no SQLite
    para listas Python.

    Utilizado principalmente para:

    - pontos_fortes;
    - pontos_melhoria.

    Caso o valor já seja uma lista,
    apenas a retorna.
    """

    if valor is None:

        return []


    if isinstance(
        valor,
        list
    ):

        return valor


    if isinstance(
        valor,
        tuple
    ):

        return list(
            valor
        )


    if isinstance(
        valor,
        str
    ):

        texto = valor.strip()


        if not texto:

            return []


        try:

            resultado = json.loads(
                texto
            )


            if isinstance(
                resultado,
                list
            ):

                return resultado


            return [
                resultado
            ]


        except json.JSONDecodeError:

            return [
                texto
            ]


    return [
        valor
    ]


# ============================================================
# BUSCAR DADOS DA ENTREVISTA
# ============================================================

def buscar_dados_entrevista(
    entrevista_id: int
):
    """
    Busca os dados básicos necessários
    para gerar o relatório.

    Esta função também é utilizada pelo router
    para verificar a existência e a propriedade
    da entrevista.
    """

    if entrevista_id <= 0:

        raise ValueError(
            "ID da entrevista inválido."
        )


    entrevista = buscar_entrevista(
        entrevista_id
    )


    if entrevista is None:

        raise ValueError(
            "Entrevista não encontrada."
        )


    return entrevista


# ============================================================
# GERAR RELATÓRIO
# ============================================================

def gerar_relatorio(
    entrevista_id: int
) -> dict:
    """
    Gera o relatório completo de uma entrevista.

    O relatório consolida:

    - dados da entrevista;
    - perguntas;
    - respostas;
    - avaliações;
    - notas por critério;
    - pontuação final;
    - classificação;
    - desempenho por critério;
    - destaques.

    Nenhuma nova avaliação de IA é realizada
    nesta função.

    O relatório utiliza somente resultados
    já armazenados pelo sistema.
    """

    # --------------------------------------------------------
    # VALIDAR ID
    # --------------------------------------------------------

    if entrevista_id <= 0:

        raise ValueError(
            "ID da entrevista inválido."
        )


    # --------------------------------------------------------
    # ENTREVISTA
    # --------------------------------------------------------

    entrevista = buscar_dados_entrevista(
        entrevista_id
    )


    # --------------------------------------------------------
    # RESPOSTAS
    # --------------------------------------------------------

    respostas = (
        listar_respostas_entrevista(
            entrevista_id
        )
    )


    # --------------------------------------------------------
    # AVALIAÇÕES
    # --------------------------------------------------------

    avaliacoes = (
        buscar_avaliacoes_entrevista(
            entrevista_id
        )
    )


    # --------------------------------------------------------
    # TODAS AS NOTAS DOS CRITÉRIOS
    # --------------------------------------------------------
    #
    # IMPORTANTE:
    #
    # buscar_notas_criterios recebe o ID
    # DA ENTREVISTA.
    #
    # Não recebe avaliacao_id.
    #
    # Buscamos uma única vez e depois filtramos
    # por avaliação.
    # --------------------------------------------------------

    todas_notas_criterios = (
        buscar_notas_criterios(
            entrevista_id
        )
        if avaliacoes
        else []
    )


    # --------------------------------------------------------
    # DETALHES DAS RESPOSTAS
    # --------------------------------------------------------

    respostas_relatorio = []


    for resposta in respostas:

        # ----------------------------------------------------
        # ID DA RESPOSTA
        # ----------------------------------------------------

        resposta_id = _valor(
            resposta,
            "id"
        )


        # ----------------------------------------------------
        # ID DA PERGUNTA
        # ----------------------------------------------------

        pergunta_id = _valor(
            resposta,
            "pergunta_id"
        )


        # ----------------------------------------------------
        # SNAPSHOT HISTÓRICO DA PERGUNTA
        # ----------------------------------------------------

        snapshot_pergunta = buscar_snapshot_resposta(
            resposta_id
        )

        if snapshot_pergunta is None:

            raise ValueError(
                "Resposta não encontrada ao gerar "
                "o relatório."
            )


        # ----------------------------------------------------
        # LOCALIZAR AVALIAÇÃO DA RESPOSTA
        # ----------------------------------------------------

        avaliacao_resposta = None


        for avaliacao in avaliacoes:

            if (
                _valor(
                    avaliacao,
                    "resposta_id"
                )
                == resposta_id
            ):

                avaliacao_resposta = (
                    avaliacao
                )

                break


        # ----------------------------------------------------
        # NOTAS DOS CRITÉRIOS
        # ----------------------------------------------------

        notas_criterios = []


        if avaliacao_resposta is not None:

            avaliacao_id = _valor(
                avaliacao_resposta,
                "id"
            )


            if avaliacao_id is None:

                avaliacao_id = _valor(
                    avaliacao_resposta,
                    "avaliacao_id"
                )


            if avaliacao_id is not None:

                notas_criterios = [

                    nota

                    for nota
                    in todas_notas_criterios

                    if (
                        _valor(
                            nota,
                            "avaliacao_id"
                        )
                        == avaliacao_id
                    )
                ]


        # ----------------------------------------------------
        # DADOS DA AVALIAÇÃO
        # ----------------------------------------------------

        avaliacao_relatorio = None


        if avaliacao_resposta is not None:

            avaliacao_relatorio = {

                "id":
                    _valor(
                        avaliacao_resposta,
                        "id",
                        _valor(
                            avaliacao_resposta,
                            "avaliacao_id"
                        )
                    ),

                "pontuacao":
                    _valor(
                        avaliacao_resposta,
                        "pontuacao"
                    ),

                "pontos_fortes":
                    _converter_lista_json(
                        _valor(
                            avaliacao_resposta,
                            "pontos_fortes"
                        )
                    ),

                "pontos_melhoria":
                    _converter_lista_json(
                        _valor(
                            avaliacao_resposta,
                            "pontos_melhoria"
                        )
                    ),

                "feedback":
                    _valor(
                        avaliacao_resposta,
                        "feedback"
                    ),

                "modelo_ia":
                    _valor(
                        avaliacao_resposta,
                        "modelo_ia"
                    ),

                "data_avaliacao":
                    _valor(
                        avaliacao_resposta,
                        "data_avaliacao"
                    ),

                "criterios":
                    notas_criterios
            }


        # ----------------------------------------------------
        # MONTAR RESPOSTA
        # ----------------------------------------------------

        respostas_relatorio.append(
            {

                "resposta_id":
                    resposta_id,

                "pergunta_id":
                    pergunta_id,

                "pergunta":
                    _valor(
                        snapshot_pergunta,
                        "pergunta"
                    ),

                "competencia_id":
                    _valor(
                        snapshot_pergunta,
                        "competencia_id"
                    ),

                "usa_star":
                    bool(
                        _valor(
                            snapshot_pergunta,
                            "usa_star",
                            False
                        )
                    ),

                "peso_pergunta":
                    _valor(
                        snapshot_pergunta,
                        "peso_pergunta",
                        1.0
                    ),

                "texto_resposta":
                    _valor(
                        resposta,
                        "texto_resposta"
                    ),

                "tempo_resposta":
                    _valor(
                        resposta,
                        "tempo_resposta"
                    ),

                "data_resposta":
                    _valor(
                        resposta,
                        "data_resposta"
                    ),

                "avaliacao":
                    avaliacao_relatorio

            }
        )


    # --------------------------------------------------------
    # PONTUAÇÃO FINAL
    # --------------------------------------------------------

    pontuacao_final = _valor(
        entrevista,
        "pontuacao_final"
    )


    # --------------------------------------------------------
    # VALORES CONSOLIDADOS PADRÃO
    # --------------------------------------------------------

    classificacao = None

    desempenho_criterios = []

    destaques = {

        "melhor_criterio":
            None,

        "criterio_a_desenvolver":
            None
    }


    # --------------------------------------------------------
    # RESULTADOS CONSOLIDADOS
    # --------------------------------------------------------

    if avaliacoes:

        # ----------------------------------------------------
        # DESEMPENHO DOS CRITÉRIOS
        # ----------------------------------------------------

        desempenho_criterios = (
            calcular_desempenho_criterios(
                entrevista_id
            )
        )


        # ----------------------------------------------------
        # CLASSIFICAÇÃO
        # ----------------------------------------------------

        if pontuacao_final is not None:

            classificacao = (
                classificar_desempenho(
                    pontuacao_final
                )
            )


        # ----------------------------------------------------
        # DESTAQUES
        # ----------------------------------------------------
        #
        # identificar_destaques recebe
        # DESEMPENHO_CRITERIOS.
        #
        # Não recebe entrevista_id.
        # ----------------------------------------------------

        destaques = identificar_destaques(
            desempenho_criterios
        )


    # --------------------------------------------------------
    # RETORNO
    # --------------------------------------------------------

    return {

        "entrevista": {

            "id":
                _valor(
                    entrevista,
                    "id"
                ),

            "usuario_id":
                _valor(
                    entrevista,
                    "usuario_id"
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
                pontuacao_final,

            "observacoes":
                _valor(
                    entrevista,
                    "observacoes"
                )

        },


        "quantidade_respostas":
            len(
                respostas
            ),


        "quantidade_avaliacoes":
            len(
                avaliacoes
            ),


        "classificacao":
            classificacao,


        "desempenho_criterios":
            desempenho_criterios,


        "destaques":
            destaques,


        "respostas":
            respostas_relatorio

    }