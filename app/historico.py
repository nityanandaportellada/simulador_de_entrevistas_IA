
"""Serviço responsável pelo histórico das entrevistas do usuário."""

import math

from .avaliacao import calcular_desempenho_criterios
from .database import conectar_banco


def _validar_id(valor: int, campo: str) -> None:
    """Valida um identificador numérico."""
    if type(valor) is not int or valor <= 0:
        raise ValueError(f"{campo} inválido.")


def _nota_visivel(registro):
    """Mostra a pontuação somente após a avaliação e recusa valores inconsistentes."""
    if registro["status"] != "avaliada":
        return None
    nota = registro["pontuacao_final"]
    if type(nota) not in (int, float) or not math.isfinite(nota) or not 0 <= nota <= 10:
        raise ValueError("Uma entrevista avaliada possui pontuação histórica inválida.")
    return float(nota)


def listar_historico(usuario_id: int) -> list[dict]:
    """Retorna as entrevistas do usuário, da mais recente para a mais antiga."""
    _validar_id(usuario_id, "ID do usuário")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Os nomes vêm dos snapshots da entrevista. Não usamos os cadastros atuais.
        cursor.execute(
            """
            SELECT id, tipo_entrevista_id, tipo_entrevista_nome_aplicado,
                   area_tecnica_id, area_tecnica_nome_aplicado,
                   subarea_tecnica_id, subarea_tecnica_nome_aplicado,
                   data_inicio, data_fim, status, pontuacao_final
            FROM entrevistas
            WHERE usuario_id = ?
            ORDER BY data_inicio DESC, id DESC
            """,
            (usuario_id,)
        )
        registros = cursor.fetchall()

        return [
            {
                "id": registro["id"],
                "tipo_entrevista_id": registro["tipo_entrevista_id"],
                "tipo_entrevista": registro["tipo_entrevista_nome_aplicado"],
                "area_tecnica_id": registro["area_tecnica_id"],
                "area_tecnica": registro["area_tecnica_nome_aplicado"],
                "subarea_tecnica_id": registro["subarea_tecnica_id"],
                "subarea_tecnica": registro["subarea_tecnica_nome_aplicado"],
                "data_inicio": registro["data_inicio"],
                "data_fim": registro["data_fim"],
                "status": registro["status"],
                "pontuacao_final": _nota_visivel(registro)
            }
            for registro in registros
        ]
    finally:
        conexao.close()


def gerar_resumo_historico(usuario_id: int) -> dict:
    """Gera os indicadores resumidos do histórico do usuário."""
    _validar_id(usuario_id, "ID do usuário")
    historico = listar_historico(usuario_id)

    entrevistas_avaliadas = [
        entrevista
        for entrevista in historico
        if entrevista["status"] == "avaliada"
        and entrevista["pontuacao_final"] is not None
    ]

    pontuacoes = [
        float(entrevista["pontuacao_final"])
        for entrevista in entrevistas_avaliadas
    ]

    if pontuacoes:
        media_pontuacoes = round(sum(pontuacoes) / len(pontuacoes), 2)
        melhor_pontuacao = round(max(pontuacoes), 2)
        # O histórico está em ordem decrescente.
        ultima_pontuacao = round(pontuacoes[0], 2)
    else:
        media_pontuacoes = None
        melhor_pontuacao = None
        ultima_pontuacao = None

    return {
        "quantidade_total": len(historico),
        "quantidade_avaliada": len(entrevistas_avaliadas),
        "media_pontuacoes": media_pontuacoes,
        "melhor_pontuacao": melhor_pontuacao,
        "ultima_pontuacao": ultima_pontuacao
    }


def obter_evolucao_pontuacoes(usuario_id: int) -> list[dict]:
    """Retorna a evolução cronológica das pontuações avaliadas."""
    _validar_id(usuario_id, "ID do usuário")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id, tipo_entrevista_id, tipo_entrevista_nome_aplicado,
                   area_tecnica_id, area_tecnica_nome_aplicado,
                   subarea_tecnica_id, subarea_tecnica_nome_aplicado,
                   data_inicio, data_fim, status, pontuacao_final
            FROM entrevistas
            WHERE usuario_id = ?
              AND status = 'avaliada'
            ORDER BY COALESCE(data_fim, data_inicio), id
            """,
            (usuario_id,)
        )
        registros = cursor.fetchall()

        return [
            {
                "entrevista_id": registro["id"],
                "data": registro["data_fim"] or registro["data_inicio"],
                "pontuacao": _nota_visivel(registro),
                "tipo_entrevista_id": registro["tipo_entrevista_id"],
                "tipo_entrevista": registro["tipo_entrevista_nome_aplicado"],
                "area_tecnica_id": registro["area_tecnica_id"],
                "area_tecnica": registro["area_tecnica_nome_aplicado"],
                "subarea_tecnica_id": registro["subarea_tecnica_id"],
                "subarea_tecnica": registro["subarea_tecnica_nome_aplicado"]
            }
            for registro in registros
        ]
    finally:
        conexao.close()


def _listar_entrevistas_avaliadas(usuario_id: int) -> list[dict]:
    """Retorna entrevistas avaliadas em ordem cronológica."""
    _validar_id(usuario_id, "ID do usuário")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id, tipo_entrevista_id, tipo_entrevista_nome_aplicado,
                   area_tecnica_id, area_tecnica_nome_aplicado,
                   subarea_tecnica_id, subarea_tecnica_nome_aplicado,
                   data_inicio, data_fim, status, pontuacao_final
            FROM entrevistas
            WHERE usuario_id = ?
              AND status = 'avaliada'
            ORDER BY COALESCE(data_fim, data_inicio), id
            """,
            (usuario_id,)
        )
        registros = cursor.fetchall()

        return [
            {
                "id": registro["id"],
                "tipo_entrevista_id": registro["tipo_entrevista_id"],
                "tipo_entrevista": registro["tipo_entrevista_nome_aplicado"],
                "area_tecnica_id": registro["area_tecnica_id"],
                "area_tecnica": registro["area_tecnica_nome_aplicado"],
                "subarea_tecnica_id": registro["subarea_tecnica_id"],
                "subarea_tecnica": registro["subarea_tecnica_nome_aplicado"],
                "data_inicio": registro["data_inicio"],
                "data_fim": registro["data_fim"],
                "pontuacao_final": _nota_visivel(registro)
            }
            for registro in registros
        ]
    finally:
        conexao.close()


def _validar_avaliacoes_historicas(entrevista_id: int, pontuacao_final: float) -> None:
    """Confere avaliações e critérios antes de exibir a evolução de uma entrevista."""
    conexao = conectar_banco()
    try:
        respostas = conexao.execute(
            """SELECT r.id AS resposta_id, r.peso_pergunta_aplicado AS peso,
                      a.id AS avaliacao_id, a.pontuacao
               FROM respostas r LEFT JOIN avaliacoes a ON a.resposta_id = r.id
               WHERE r.entrevista_id = ?""", (entrevista_id,)
        ).fetchall()
        if not respostas or any(registro["avaliacao_id"] is None for registro in respostas):
            raise ValueError("Existem respostas sem avaliação histórica.")

        notas = conexao.execute(
            """SELECT ac.avaliacao_id, ac.criterio_id, ac.nota, ac.peso_aplicado
               FROM avaliacao_criterios ac
               INNER JOIN avaliacoes a ON a.id = ac.avaliacao_id
               INNER JOIN respostas r ON r.id = a.resposta_id
               WHERE r.entrevista_id = ?""", (entrevista_id,)
        ).fetchall()
        notas_por_avaliacao = {}
        for nota in notas:
            lista = notas_por_avaliacao.setdefault(nota["avaliacao_id"], [])
            if any(item["criterio_id"] == nota["criterio_id"] for item in lista):
                raise ValueError("Existe critério histórico duplicado.")
            lista.append(nota)

        conjunto_criterios = None
        soma_ponderada = 0.0
        soma_pesos = 0.0
        for resposta in respostas:
            avaliacao_id = resposta["avaliacao_id"]
            criterios = notas_por_avaliacao.get(avaliacao_id, [])
            if not criterios:
                raise ValueError("Existem avaliações sem critérios históricos.")
            ids_criterios = {nota["criterio_id"] for nota in criterios}
            if conjunto_criterios is None:
                conjunto_criterios = ids_criterios
            elif ids_criterios != conjunto_criterios:
                raise ValueError("As avaliações possuem critérios históricos diferentes.")

            soma_notas = 0.0
            soma_pesos_criterios = 0.0
            for criterio in criterios:
                nota = criterio["nota"]
                peso_criterio = criterio["peso_aplicado"]
                if (type(nota) not in (float, int) or not math.isfinite(nota) or not 0 <= nota <= 10
                    or type(peso_criterio) not in (float, int) or not math.isfinite(peso_criterio)
                    or peso_criterio < 0):
                    raise ValueError("Nota ou peso histórico de critério inválido.")
                soma_notas += nota * peso_criterio
                soma_pesos_criterios += peso_criterio
            if not math.isfinite(soma_notas) or not math.isfinite(soma_pesos_criterios) or soma_pesos_criterios <= 0:
                raise ValueError("Pesos históricos dos critérios inválidos.")

            pontuacao = resposta["pontuacao"]
            peso = resposta["peso"]
            if (type(pontuacao) not in (float, int) or not math.isfinite(pontuacao)
                or not 0 <= pontuacao <= 10 or type(peso) not in (float, int)
                or not math.isfinite(peso) or peso < 0):
                raise ValueError("Pontuação ou peso histórico da resposta inválido.")
            if abs(round(soma_notas / soma_pesos_criterios, 2) - pontuacao) > 0.02:
                raise ValueError("A nota da resposta não corresponde aos critérios históricos.")
            soma_ponderada += pontuacao * peso
            soma_pesos += peso

        if (not math.isfinite(soma_pesos) or not math.isfinite(soma_ponderada) or soma_pesos <= 0
            or abs(round(soma_ponderada / soma_pesos, 2) - pontuacao_final) > 0.02):
            raise ValueError("A nota geral não corresponde às avaliações históricas.")
    finally:
        conexao.close()


def obter_evolucao_criterios(usuario_id: int) -> list[dict]:
    """Retorna somente critérios de avaliações completas do usuário autenticado."""
    _validar_id(usuario_id, "ID do usuário")
    entrevistas = _listar_entrevistas_avaliadas(usuario_id)
    evolucao = []

    for entrevista in entrevistas:
        entrevista_id = entrevista["id"]
        # Os IDs vêm da consulta filtrada pelo proprietário; não recebem IDs do cliente.
        _validar_avaliacoes_historicas(entrevista_id, entrevista["pontuacao_final"])
        criterios = calcular_desempenho_criterios(entrevista_id)
        evolucao.append({
            "entrevista_id": entrevista_id,
            "data": entrevista["data_fim"] or entrevista["data_inicio"],
            "tipo_entrevista_id": entrevista["tipo_entrevista_id"],
            "tipo_entrevista": entrevista["tipo_entrevista"],
            "area_tecnica_id": entrevista["area_tecnica_id"],
            "area_tecnica": entrevista["area_tecnica"],
            "subarea_tecnica_id": entrevista["subarea_tecnica_id"],
            "subarea_tecnica": entrevista["subarea_tecnica"],
            "criterios": criterios
        })
    return evolucao
