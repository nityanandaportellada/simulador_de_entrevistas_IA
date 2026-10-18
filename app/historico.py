"""Serviço responsável pelo histórico das entrevistas do usuário."""

from .avaliacao import calcular_desempenho_criterios
from .database import conectar_banco


def _validar_id(valor: int, campo: str) -> None:
    """Valida um identificador numérico."""
    if not isinstance(valor, int) or valor <= 0:
        raise ValueError(f"{campo} inválido.")


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
                "pontuacao_final": registro["pontuacao_final"]
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
                   data_inicio, data_fim, pontuacao_final
            FROM entrevistas
            WHERE usuario_id = ?
              AND status = 'avaliada'
              AND pontuacao_final IS NOT NULL
            ORDER BY COALESCE(data_fim, data_inicio), id
            """,
            (usuario_id,)
        )
        registros = cursor.fetchall()

        return [
            {
                "entrevista_id": registro["id"],
                "data": registro["data_fim"] or registro["data_inicio"],
                "pontuacao": registro["pontuacao_final"],
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
                   data_inicio, data_fim, pontuacao_final
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
                "pontuacao_final": registro["pontuacao_final"]
            }
            for registro in registros
        ]
    finally:
        conexao.close()


def obter_evolucao_criterios(usuario_id: int) -> list[dict]:
    """Retorna a evolução dos critérios nas entrevistas avaliadas."""
    _validar_id(usuario_id, "ID do usuário")
    entrevistas = _listar_entrevistas_avaliadas(usuario_id)
    evolucao = []

    for entrevista in entrevistas:
        entrevista_id = entrevista["id"]

        # Inconsistências históricas não devem ser escondidas.
        criterios = calcular_desempenho_criterios(entrevista_id)

        evolucao.append(
            {
                "entrevista_id": entrevista_id,
                "data": entrevista["data_fim"] or entrevista["data_inicio"],
                "tipo_entrevista_id": entrevista["tipo_entrevista_id"],
                "tipo_entrevista": entrevista["tipo_entrevista"],
                "area_tecnica_id": entrevista["area_tecnica_id"],
                "area_tecnica": entrevista["area_tecnica"],
                "subarea_tecnica_id": entrevista["subarea_tecnica_id"],
                "subarea_tecnica": entrevista["subarea_tecnica"],
                "criterios": criterios
            }
        )

    return evolucao