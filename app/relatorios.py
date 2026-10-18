
"""Funções responsáveis por montar os relatórios históricos das entrevistas."""

import json

from .avaliacao import (
    buscar_avaliacoes_entrevista,
    buscar_notas_criterios,
    calcular_desempenho_criterios,
    classificar_desempenho,
    identificar_destaques
)
from .entrevistas import buscar_entrevista, listar_perguntas_entrevista
from .respostas import listar_respostas_entrevista


def _valor(objeto, atributo, padrao=None):
    """Obtém um valor de um dicionário ou de um objeto Python."""
    if objeto is None:
        return padrao
    if isinstance(objeto, dict):
        return objeto.get(atributo, padrao)
    return getattr(objeto, atributo, padrao)


def _converter_lista_json(valor) -> list:
    """Converte um valor JSON salvo no banco para uma lista Python."""
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    if isinstance(valor, tuple):
        return list(valor)
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return []
        try:
            resultado = json.loads(texto)
            if isinstance(resultado, list):
                return resultado
            return [resultado]
        except json.JSONDecodeError:
            return [texto]
    return [valor]


def buscar_dados_entrevista(entrevista_id: int):
    """Busca uma entrevista e valida o ID antes de devolver os dados."""
    if not isinstance(entrevista_id, int) or entrevista_id <= 0:
        raise ValueError("ID da entrevista inválido.")
    entrevista = buscar_entrevista(entrevista_id)
    if entrevista is None:
        raise ValueError("Entrevista não encontrada.")
    return entrevista


def _contar_perguntas_historicas(perguntas_congeladas, respostas) -> int:
    """Conta perguntas pelo conjunto congelado e usa as respostas em entrevistas antigas."""
    if perguntas_congeladas:
        return len(perguntas_congeladas)

    # Entrevistas antigas podem não possuir registros em entrevista_perguntas.
    perguntas_ids = set()
    for resposta in respostas:
        pergunta_id = _valor(resposta, "pergunta_id")
        if pergunta_id is not None:
            perguntas_ids.add(pergunta_id)
    return len(perguntas_ids)


def gerar_relatorio(entrevista_id: int) -> dict:
    """Monta o relatório completo usando snapshots e compatibilidade com entrevistas antigas."""
    if not isinstance(entrevista_id, int) or entrevista_id <= 0:
        raise ValueError("ID da entrevista inválido.")

    entrevista = buscar_dados_entrevista(entrevista_id)

    # As entrevistas atuais possuem o conjunto de perguntas congelado no início.
    perguntas_congeladas = listar_perguntas_entrevista(entrevista_id)
    perguntas_por_id = {}

    for pergunta in perguntas_congeladas:
        pergunta_id = _valor(pergunta, "pergunta_id")
        if pergunta_id is not None:
            perguntas_por_id[pergunta_id] = pergunta

    respostas = listar_respostas_entrevista(entrevista_id)
    quantidade_perguntas = _contar_perguntas_historicas(perguntas_congeladas, respostas)
    avaliacoes = buscar_avaliacoes_entrevista(entrevista_id)

    # Só existem notas de critérios quando existem avaliações.
    if avaliacoes:
        todas_notas_criterios = buscar_notas_criterios(entrevista_id)
    else:
        todas_notas_criterios = []

    respostas_relatorio = []

    for resposta in respostas:
        resposta_id = _valor(resposta, "id")
        pergunta_id = _valor(resposta, "pergunta_id")
        pergunta_congelada = perguntas_por_id.get(pergunta_id)

        # Localiza a avaliação que pertence à resposta atual.
        avaliacao_resposta = None
        for avaliacao in avaliacoes:
            if _valor(avaliacao, "resposta_id") == resposta_id:
                avaliacao_resposta = avaliacao
                break

        notas_criterios = []
        if avaliacao_resposta is not None:
            avaliacao_id = _valor(
                avaliacao_resposta, "avaliacao_id",
                _valor(avaliacao_resposta, "id")
            )
            for nota in todas_notas_criterios:
                if _valor(nota, "avaliacao_id") == avaliacao_id:
                    notas_criterios.append(nota)

        # A resposta mantém os snapshots históricos da pergunta e da competência.
        pergunta_texto = _valor(resposta, "pergunta_texto_aplicado")
        exemplo_esperado = _valor(resposta, "exemplo_esperado_aplicado")
        competencia_id = _valor(resposta, "competencia_id_aplicada")
        competencia_nome = _valor(resposta, "competencia_nome_aplicada")
        peso_pergunta = _valor(resposta, "peso_pergunta_aplicado")
        usa_star = _valor(resposta, "usa_star_aplicado")
        ordem_pergunta = _valor(resposta, "ordem_pergunta_aplicada")

        if pergunta_texto is None:
            raise ValueError("Existe resposta sem snapshot histórico do texto da pergunta.")
        if peso_pergunta is None:
            raise ValueError("Existe resposta sem peso histórico da pergunta.")

        # Área e subárea da pergunta vêm do conjunto congelado quando ele existe.
        if pergunta_congelada is not None:
            area_pergunta_id = _valor(pergunta_congelada, "area_tecnica_id_aplicada")
            area_pergunta = _valor(pergunta_congelada, "area_tecnica_nome_aplicada")
            subarea_pergunta_id = _valor(pergunta_congelada, "subarea_tecnica_id_aplicada")
            subarea_pergunta = _valor(pergunta_congelada, "subarea_tecnica_nome_aplicada")
        else:
            # Entrevistas antigas não possuem esse snapshot individual da pergunta.
            area_pergunta_id = None
            area_pergunta = None
            subarea_pergunta_id = None
            subarea_pergunta = None

        # Somente perguntas técnicas com contexto histórico completo podem não ter competência.
        tecnica = (
            pergunta_congelada is not None
            and area_pergunta_id is not None
            and subarea_pergunta_id is not None
            and area_pergunta is not None
            and subarea_pergunta is not None
        )
        if competencia_id is None and (not tecnica or competencia_nome is not None):
            raise ValueError("Existe resposta sem snapshot histórico da competência.")
        if competencia_nome is None and (not tecnica or competencia_id is not None):
            raise ValueError("Existe resposta sem nome histórico da competência.")

        avaliacao_formatada = None
        if avaliacao_resposta is not None:
            avaliacao_formatada = {
                "id": _valor(
                    avaliacao_resposta, "avaliacao_id",
                    _valor(avaliacao_resposta, "id")
                ),
                "pontuacao": _valor(avaliacao_resposta, "pontuacao"),
                "pontos_fortes": _converter_lista_json(
                    _valor(avaliacao_resposta, "pontos_fortes")
                ),
                "pontos_melhoria": _converter_lista_json(
                    _valor(avaliacao_resposta, "pontos_melhoria")
                ),
                "feedback": _valor(avaliacao_resposta, "feedback"),
                "modelo_ia": _valor(avaliacao_resposta, "modelo_ia"),
                "data_avaliacao": _valor(avaliacao_resposta, "data_avaliacao"),
                "criterios": notas_criterios
            }

        respostas_relatorio.append({
            "resposta_id": resposta_id,
            "pergunta_id": pergunta_id,
            "pergunta": pergunta_texto,
            "exemplo_esperado": exemplo_esperado,
            "competencia_id": competencia_id,
            "competencia": competencia_nome,
            "usa_star": usa_star,
            "peso_pergunta": peso_pergunta,
            "ordem_pergunta": ordem_pergunta,
            "area_tecnica_id": area_pergunta_id,
            "area_tecnica": area_pergunta,
            "subarea_tecnica_id": subarea_pergunta_id,
            "subarea_tecnica": subarea_pergunta,
            "texto_resposta": _valor(resposta, "texto_resposta"),
            "tempo_resposta": _valor(resposta, "tempo_resposta"),
            "data_resposta": _valor(resposta, "data_resposta"),
            "avaliacao": avaliacao_formatada
        })

    # Os valores consolidados só são calculados quando existem avaliações.
    pontuacao_final = _valor(entrevista, "pontuacao_final")
    classificacao = None
    desempenho_criterios = []
    destaques = {
        "melhor_criterio": None,
        "criterio_a_desenvolver": None
    }

    if avaliacoes:
        # Erros de integridade histórica não são escondidos pelo relatório.
        desempenho_criterios = calcular_desempenho_criterios(entrevista_id)

        if pontuacao_final is not None:
            classificacao = classificar_desempenho(pontuacao_final)

        destaques = identificar_destaques(desempenho_criterios)

    return {
        "entrevista": {
            "id": _valor(entrevista, "id"),
            "usuario_id": _valor(entrevista, "usuario_id"),
            "tipo_entrevista_id": _valor(entrevista, "tipo_entrevista_id"),
            "tipo_entrevista": _valor(entrevista, "tipo_entrevista_nome_aplicado"),
            "tipo_entrevista_descricao": _valor(
                entrevista, "tipo_entrevista_descricao_aplicada"
            ),
            "area_tecnica_id": _valor(entrevista, "area_tecnica_id"),
            "area_tecnica": _valor(entrevista, "area_tecnica_nome_aplicado"),
            "subarea_tecnica_id": _valor(entrevista, "subarea_tecnica_id"),
            "subarea_tecnica": _valor(entrevista, "subarea_tecnica_nome_aplicado"),
            "data_inicio": _valor(entrevista, "data_inicio"),
            "data_fim": _valor(entrevista, "data_fim"),
            "status": _valor(entrevista, "status"),
            "pontuacao_final": pontuacao_final,
            "observacoes": _valor(entrevista, "observacoes")
        },
        "quantidade_perguntas": quantidade_perguntas,
        "quantidade_respostas": len(respostas),
        "quantidade_avaliacoes": len(avaliacoes),
        "classificacao": classificacao,
        "desempenho_criterios": desempenho_criterios,
        "destaques": destaques,
        "respostas": respostas_relatorio
    }
