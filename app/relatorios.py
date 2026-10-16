"""
relatorios.py

Serviço responsável pela geração dos relatórios
do Simulador de Entrevistas.

Versão: 0.8

Responsabilidades:

- buscar os dados históricos da entrevista;
- apresentar tipo de entrevista;
- apresentar área e subárea técnica;
- reunir perguntas congeladas;
- manter compatibilidade com entrevistas antigas;
- reunir respostas;
- reunir avaliações realizadas pela IA;
- reunir notas por critério;
- apresentar a pontuação final;
- apresentar classificação;
- apresentar desempenho consolidado por critério;
- identificar melhor critério;
- identificar critério a desenvolver;
- preservar informações históricas;
- organizar os dados utilizados pelo frontend.

IMPORTANTE:

Este módulo não realiza nova análise por IA.

Ele utiliza somente dados já armazenados
no banco de dados.

ENTREVISTAS NOVAS:

As perguntas são obtidas prioritariamente de:

    entrevista_perguntas

ENTREVISTAS ANTIGAS:

Entrevistas criadas antes da implementação de
entrevista_perguntas podem não possuir registros
nessa tabela.

Nesse caso, os snapshots existentes em respostas
são utilizados como fallback histórico.

Nenhuma inconsistência de avaliação é escondida.
Caso o Motor de Pontuação identifique dados
históricos inválidos, o erro será propagado.
"""

import json


from .entrevistas import (
    buscar_entrevista,
    listar_perguntas_entrevista
)


from .respostas import (
    listar_respostas_entrevista
)


from .avaliacao import (
    buscar_avaliacoes_entrevista,
    buscar_notas_criterios,
    calcular_desempenho_criterios,
    classificar_desempenho,
    identificar_destaques
)


# ============================================================
# OBTER VALOR
# ============================================================

def _valor(
    objeto,
    atributo,
    padrao=None
):
    """
    Obtém um valor de um dicionário
    ou objeto Python.
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
# CONVERTER JSON PARA LISTA
# ============================================================

def _converter_lista_json(
    valor
) -> list:
    """
    Converte campos JSON armazenados no SQLite
    para listas Python.
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
    Busca os dados básicos da entrevista.

    Também é utilizada pelo router
    para verificar existência e propriedade.
    """

    if (
        not isinstance(
            entrevista_id,
            int
        )
        or entrevista_id <= 0
    ):

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
# CONTAR PERGUNTAS HISTÓRICAS
# ============================================================

def _contar_perguntas_historicas(
    perguntas_congeladas,
    respostas
) -> int:
    """
    Determina a quantidade histórica de perguntas.

    Prioridade:

    1. entrevista_perguntas;
    2. snapshots existentes nas respostas.

    O fallback permite manter compatibilidade
    com entrevistas criadas antes da existência
    de entrevista_perguntas.
    """

    if perguntas_congeladas:

        return len(
            perguntas_congeladas
        )


    perguntas_ids = {

        _valor(
            resposta,
            "pergunta_id"
        )

        for resposta
        in respostas

        if (
            _valor(
                resposta,
                "pergunta_id"
            )
            is not None
        )

    }


    return len(
        perguntas_ids
    )


# ============================================================
# GERAR RELATÓRIO
# ============================================================

def gerar_relatorio(
    entrevista_id: int
) -> dict:
    """
    Gera o relatório completo de uma entrevista.

    O relatório utiliza:

    - snapshot do tipo;
    - snapshot da área;
    - snapshot da subárea;
    - perguntas congeladas;
    - snapshots das respostas;
    - snapshots dos critérios.

    Para entrevistas antigas sem registros em
    entrevista_perguntas, utiliza os snapshots
    presentes nas respostas.
    """

    if (
        not isinstance(
            entrevista_id,
            int
        )
        or entrevista_id <= 0
    ):

        raise ValueError(
            "ID da entrevista inválido."
        )


    # ========================================================
    # ENTREVISTA
    # ========================================================

    entrevista = buscar_dados_entrevista(
        entrevista_id
    )


    # ========================================================
    # PERGUNTAS CONGELADAS
    # ========================================================

    perguntas_congeladas = (
        listar_perguntas_entrevista(
            entrevista_id
        )
    )


    perguntas_por_id = {

        _valor(
            pergunta,
            "pergunta_id"
        ):
            pergunta

        for pergunta
        in perguntas_congeladas

        if (
            _valor(
                pergunta,
                "pergunta_id"
            )
            is not None
        )

    }


    # ========================================================
    # RESPOSTAS
    # ========================================================

    respostas = listar_respostas_entrevista(
        entrevista_id
    )


    # ========================================================
    # QUANTIDADE HISTÓRICA DE PERGUNTAS
    # ========================================================

    quantidade_perguntas = (
        _contar_perguntas_historicas(

            perguntas_congeladas,

            respostas

        )
    )


    # ========================================================
    # AVALIAÇÕES
    # ========================================================

    avaliacoes = (
        buscar_avaliacoes_entrevista(
            entrevista_id
        )
    )


    # ========================================================
    # NOTAS DOS CRITÉRIOS
    # ========================================================

    if avaliacoes:

        todas_notas_criterios = (
            buscar_notas_criterios(
                entrevista_id
            )
        )


    else:

        todas_notas_criterios = []


    # ========================================================
    # MONTAR RESPOSTAS
    # ========================================================

    respostas_relatorio = []


    for resposta in respostas:

        resposta_id = _valor(
            resposta,
            "id"
        )


        pergunta_id = _valor(
            resposta,
            "pergunta_id"
        )


        pergunta_congelada = (
            perguntas_por_id.get(
                pergunta_id
            )
        )


        # ====================================================
        # LOCALIZAR AVALIAÇÃO
        # ====================================================

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


        # ====================================================
        # CRITÉRIOS DA AVALIAÇÃO
        # ====================================================

        notas_criterios = []


        if (
            avaliacao_resposta
            is not None
        ):

            avaliacao_id = _valor(

                avaliacao_resposta,

                "avaliacao_id",

                _valor(
                    avaliacao_resposta,
                    "id"
                )

            )


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


        # ====================================================
        # DADOS HISTÓRICOS DA RESPOSTA
        # ====================================================

        pergunta_texto = _valor(
            resposta,
            "pergunta_texto_aplicado"
        )


        exemplo_esperado = _valor(
            resposta,
            "exemplo_esperado_aplicado"
        )


        competencia_id = _valor(
            resposta,
            "competencia_id_aplicada"
        )


        competencia_nome = _valor(
            resposta,
            "competencia_nome_aplicada"
        )


        peso_pergunta = _valor(
            resposta,
            "peso_pergunta_aplicado"
        )


        usa_star = _valor(
            resposta,
            "usa_star_aplicado"
        )


        ordem_pergunta = _valor(
            resposta,
            "ordem_pergunta_aplicada"
        )


        # ====================================================
        # VALIDAR SNAPSHOT DA RESPOSTA
        # ====================================================

        if pergunta_texto is None:

            raise ValueError(
                "Existe resposta sem snapshot histórico "
                "do texto da pergunta."
            )


        if competencia_id is None:

            raise ValueError(
                "Existe resposta sem snapshot histórico "
                "da competência."
            )


        if competencia_nome is None:

            raise ValueError(
                "Existe resposta sem nome histórico "
                "da competência."
            )


        if peso_pergunta is None:

            raise ValueError(
                "Existe resposta sem peso histórico "
                "da pergunta."
            )


        # ====================================================
        # ÁREA/SUBÁREA DA PERGUNTA CONGELADA
        # ====================================================

        if pergunta_congelada is not None:

            area_pergunta_id = _valor(
                pergunta_congelada,
                "area_tecnica_id_aplicada"
            )


            area_pergunta = _valor(
                pergunta_congelada,
                "area_tecnica_nome_aplicada"
            )


            subarea_pergunta_id = _valor(
                pergunta_congelada,
                "subarea_tecnica_id_aplicada"
            )


            subarea_pergunta = _valor(
                pergunta_congelada,
                "subarea_tecnica_nome_aplicada"
            )


        else:

            # ------------------------------------------------
            # ENTREVISTA LEGADA
            # ------------------------------------------------
            #
            # Não inventamos a subárea individual da
            # pergunta quando esse snapshot não existia.
            # ------------------------------------------------

            area_pergunta_id = None

            area_pergunta = None

            subarea_pergunta_id = None

            subarea_pergunta = None


        # ====================================================
        # AVALIAÇÃO FORMATADA
        # ====================================================

        avaliacao_formatada = None


        if (
            avaliacao_resposta
            is not None
        ):

            avaliacao_formatada = {

                "id":
                    _valor(

                        avaliacao_resposta,

                        "avaliacao_id",

                        _valor(
                            avaliacao_resposta,
                            "id"
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


        # ====================================================
        # ADICIONAR AO RELATÓRIO
        # ====================================================

        respostas_relatorio.append(

            {

                "resposta_id":
                    resposta_id,

                "pergunta_id":
                    pergunta_id,

                "pergunta":
                    pergunta_texto,

                "exemplo_esperado":
                    exemplo_esperado,

                "competencia_id":
                    competencia_id,

                "competencia":
                    competencia_nome,

                "usa_star":
                    usa_star,

                "peso_pergunta":
                    peso_pergunta,

                "ordem_pergunta":
                    ordem_pergunta,

                "area_tecnica_id":
                    area_pergunta_id,

                "area_tecnica":
                    area_pergunta,

                "subarea_tecnica_id":
                    subarea_pergunta_id,

                "subarea_tecnica":
                    subarea_pergunta,

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
                    avaliacao_formatada

            }

        )


    # ========================================================
    # RESULTADOS CONSOLIDADOS
    # ========================================================

    pontuacao_final = _valor(
        entrevista,
        "pontuacao_final"
    )


    classificacao = None

    desempenho_criterios = []

    destaques = {

        "melhor_criterio":
            None,

        "criterio_a_desenvolver":
            None

    }


    # ========================================================
    # NÃO ESCONDER INCONSISTÊNCIAS
    # ========================================================

    if avaliacoes:

        desempenho_criterios = (
            calcular_desempenho_criterios(
                entrevista_id
            )
        )


        if (
            pontuacao_final
            is not None
        ):

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


    # ========================================================
    # RETORNO
    # ========================================================

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

            "tipo_entrevista":
                _valor(
                    entrevista,
                    "tipo_entrevista_nome_aplicado"
                ),

            "tipo_entrevista_descricao":
                _valor(
                    entrevista,
                    "tipo_entrevista_descricao_aplicada"
                ),

            "area_tecnica_id":
                _valor(
                    entrevista,
                    "area_tecnica_id"
                ),

            "area_tecnica":
                _valor(
                    entrevista,
                    "area_tecnica_nome_aplicado"
                ),

            "subarea_tecnica_id":
                _valor(
                    entrevista,
                    "subarea_tecnica_id"
                ),

            "subarea_tecnica":
                _valor(
                    entrevista,
                    "subarea_tecnica_nome_aplicado"
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

        "quantidade_perguntas":
            quantidade_perguntas,

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