
"""Indicadores de gestão do simulador, disponíveis somente para administradores."""

import math
import sqlite3
from typing import Literal
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Path as ParametroCaminho

from ..database import conectar_banco
from ..entrevistas import (
    PERFIS_PERGUNTAS, _buscar_perguntas_tipo_normal, _buscar_perguntas_tipo_tecnico,
    _selecionar_perguntas, _selecionar_perguntas_lideranca
)
from ..limites_analise import _obter_limites
from ..models import Usuario
from ..security import obter_administrador_atual

router = APIRouter(prefix="/admin/painel", tags=["Painel administrativo"])


def _contar(conexao: sqlite3.Connection, sql: str, parametros: tuple = ()) -> int:
    """Executa uma contagem no banco sem modificar informações."""
    return int(conexao.execute(sql, parametros).fetchone()[0])


def _existe_tabela(conexao: sqlite3.Connection, nome: str) -> bool:
    return conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nome,)
    ).fetchone() is not None


def _cobertura_perguntas(conexao: sqlite3.Connection) -> dict:
    """Usa o seletor real para verificar oito perguntas por modalidade, contexto e perfil."""
    tipos = conexao.execute("SELECT id, nome, usa_area_tecnica FROM tipos_entrevista WHERE ativo = 1").fetchall()
    areas = conexao.execute("SELECT id, nome FROM areas_tecnicas WHERE ativo = 1").fetchall()
    subareas = conexao.execute(
        "SELECT id, nome, area_tecnica_id, eh_geral FROM subareas_tecnicas WHERE ativo = 1"
    ).fetchall()
    prontas, total, problemas = 0, 0, []
    for tipo in tipos:
        contextos = [(None, None, None)]
        if tipo["usa_area_tecnica"]:
            contextos = []
            for area in areas:
                associadas = [s for s in subareas if s["area_tecnica_id"] == area["id"]]
                geral = next((s for s in associadas if s["eh_geral"]), None)
                if not associadas:
                    contextos.append((area, None, geral))
                else:
                    contextos.extend((area, s, geral) for s in associadas)
        for area, subarea, geral in contextos:
            cursor = conexao.cursor()
            if not tipo["usa_area_tecnica"]:
                perguntas = _buscar_perguntas_tipo_normal(cursor, tipo["id"])
            elif geral is not None and subarea is not None:
                perguntas = _buscar_perguntas_tipo_tecnico(
                    cursor, tipo["id"], area["id"], subarea["id"], geral["id"]
                )
            else:
                perguntas = []
            for perfil in PERFIS_PERGUNTAS:
                total += 1
                try:
                    if tipo["usa_area_tecnica"] and (geral is None or subarea is None):
                        raise ValueError("Falta subárea Geral ativa ou subárea disponível.")
                    nome_normalizado = tipo["nome"].strip().casefold()
                    if nome_normalizado in ("liderança", "lideranca") and not tipo["usa_area_tecnica"]:
                        selecionadas = _selecionar_perguntas_lideranca(perguntas, perfil)
                    else:
                        selecionadas = _selecionar_perguntas(
                            perguntas, perfil, nome_normalizado == "comportamental" and not tipo["usa_area_tecnica"]
                        )
                    if len(selecionadas) != 8:
                        raise ValueError("A seleção não retornou oito perguntas.")
                    prontas += 1
                except ValueError as erro:
                    problemas.append({
                        "tipo": tipo["nome"], "area": area["nome"] if area else None,
                        "subarea": subarea["nome"] if subarea else None,
                        "perfil": perfil, "motivo": str(erro)
                    })
    return {
        "total_contextos": total, "contextos_prontos": prontas,
        "total_pendentes": len(problemas), "pendentes": problemas[:30]
    }


@router.get("")
def consultar_painel(
    dias: int = Query(default=30, ge=7, le=365),
    data_inicio: date | None = None,
    data_fim: date | None = None,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Consulta indicadores agregados e atividade recente, sem expor respostas de estudantes."""
    hoje = datetime.now(timezone.utc).date()
    if data_inicio is not None or data_fim is not None:
        if data_inicio is None or data_fim is None:
            raise HTTPException(status_code=422, detail="Informe as duas datas do período personalizado.")
        dias = (data_fim - data_inicio).days + 1
        if not 1 <= dias <= 365:
            raise HTTPException(status_code=422, detail="O período deve ter de 1 a 365 dias.")
        inicio, ultimo_dia = data_inicio, data_fim
    else:
        if dias not in (7, 30, 90, 365):
            raise HTTPException(status_code=422, detail="Escolha 7, 30, 90 ou 365 dias.")
        inicio, ultimo_dia = hoje - timedelta(days=dias - 1), hoje
    desde = inicio.isoformat() + " 00:00:00"
    ate = (ultimo_dia + timedelta(days=1)).isoformat() + " 00:00:00"
    conexao = conectar_banco()
    try:
        cadastros = {
            "usuarios": _contar(conexao, "SELECT COUNT(*) FROM usuarios"),
            "usuarios_ativos": _contar(conexao, "SELECT COUNT(*) FROM usuarios WHERE ativo = 1"),
            "tipos": _contar(conexao, "SELECT COUNT(*) FROM tipos_entrevista"),
            "competencias": _contar(conexao, "SELECT COUNT(*) FROM competencias"),
            "criterios": _contar(conexao, "SELECT COUNT(*) FROM criterios_avaliacao"),
            "perguntas": _contar(conexao, "SELECT COUNT(*) FROM perguntas"),
            "perguntas_ativas": _contar(conexao, "SELECT COUNT(*) FROM perguntas WHERE ativa = 1"),
            "perguntas_inativas": _contar(conexao, "SELECT COUNT(*) FROM perguntas WHERE ativa = 0"),
            "sem_referencia": _contar(conexao, "SELECT COUNT(*) FROM perguntas WHERE ativa = 1 AND (exemplo_esperado IS NULL OR TRIM(exemplo_esperado) = '')")
        }
        soma_pesos = conexao.execute(
            "SELECT COALESCE(SUM(peso), 0) FROM criterios_avaliacao WHERE ativo = 1"
        ).fetchone()[0]
        cadastros["soma_pesos_criterios"] = round(float(soma_pesos), 4)

        total = _contar(conexao, "SELECT COUNT(*) FROM entrevistas")
        periodos = {
            "iniciadas_periodo": _contar(conexao, "SELECT COUNT(*) FROM entrevistas WHERE data_inicio >= ? AND data_inicio < ?", (desde, ate)),
            "avaliadas_periodo": _contar(conexao, "SELECT COUNT(*) FROM entrevistas WHERE status = 'avaliada' AND data_fim >= ? AND data_fim < ?", (desde, ate)),
        }
        status_registros = conexao.execute(
            "SELECT status, COUNT(*) AS quantidade FROM entrevistas GROUP BY status"
        ).fetchall()
        situacoes = {registro["status"]: registro["quantidade"] for registro in status_registros}
        notas = [float(linha[0]) for linha in conexao.execute(
            "SELECT pontuacao_final FROM entrevistas WHERE status = 'avaliada' AND data_fim >= ? AND data_fim < ? AND pontuacao_final BETWEEN 0 AND 10", (desde, ate)
        ) if linha[0] is not None and math.isfinite(float(linha[0]))]
        entrevistas = {
            "total": total, **periodos,
            "em_andamento": situacoes.get("em_andamento", 0),
            "finalizadas_pendentes": situacoes.get("finalizada", 0),
            "em_analise": situacoes.get("em_analise", 0),
            "erro_analise": situacoes.get("erro_analise", 0),
            "avaliadas_total": situacoes.get("avaliada", 0),
            "canceladas": situacoes.get("cancelada", 0),
            "nota_media_periodo": round(sum(notas) / len(notas), 2) if notas else None
        }
        serie = []
        iniciadas = {r["dia"]: r["quantidade"] for r in conexao.execute(
            "SELECT SUBSTR(data_inicio, 1, 10) AS dia, COUNT(*) AS quantidade FROM entrevistas WHERE data_inicio >= ? AND data_inicio < ? GROUP BY dia", (desde, ate)
        )}
        avaliadas = {r["dia"]: r["quantidade"] for r in conexao.execute(
            "SELECT SUBSTR(data_fim, 1, 10) AS dia, COUNT(*) AS quantidade FROM entrevistas WHERE status = 'avaliada' AND data_fim >= ? AND data_fim < ? GROUP BY dia", (desde, ate)
        )}
        for deslocamento in range(dias):
            dia = (inicio + timedelta(days=deslocamento)).isoformat()
            serie.append({"dia": dia, "iniciadas": iniciadas.get(dia, 0), "avaliadas": avaliadas.get(dia, 0)})

        modalidades = [dict(linha) for linha in conexao.execute(
            """SELECT COALESCE(NULLIF(e.tipo_entrevista_nome_aplicado, ''), t.nome, 'Tipo não identificado') AS nome,
                      COUNT(*) AS quantidade FROM entrevistas e
               LEFT JOIN tipos_entrevista t ON t.id = e.tipo_entrevista_id
               WHERE e.data_inicio >= ? AND e.data_inicio < ? GROUP BY nome ORDER BY quantidade DESC""", (desde, ate)
        )]
        perfis = [dict(linha) for linha in conexao.execute(
            """SELECT COALESCE(perfil_profissional, 'legado') AS nome, COUNT(*) AS quantidade
               FROM entrevistas WHERE data_inicio >= ? AND data_inicio < ? GROUP BY nome ORDER BY quantidade DESC""", (desde, ate)
        )]
        areas = [dict(linha) for linha in conexao.execute(
            """SELECT COALESCE(NULLIF(e.area_tecnica_nome_aplicado, ''), a.nome, 'Sem área técnica') AS nome,
                      COUNT(*) AS quantidade FROM entrevistas e
               LEFT JOIN areas_tecnicas a ON a.id = e.area_tecnica_id
               WHERE e.data_inicio >= ? AND e.data_inicio < ? GROUP BY nome ORDER BY quantidade DESC""", (desde, ate)
        )]
        medias_modalidades = [dict(linha) for linha in conexao.execute(
            """SELECT COALESCE(NULLIF(e.tipo_entrevista_nome_aplicado, ''), t.nome, 'Tipo não identificado') AS nome,
                      ROUND(AVG(e.pontuacao_final), 2) AS media, COUNT(*) AS quantidade
               FROM entrevistas e LEFT JOIN tipos_entrevista t ON t.id = e.tipo_entrevista_id
               WHERE e.status = 'avaliada' AND e.pontuacao_final BETWEEN 0 AND 10
                 AND e.data_fim >= ? AND e.data_fim < ?
               GROUP BY nome ORDER BY media DESC""", (desde, ate)
        )]
        medias_areas = [dict(linha) for linha in conexao.execute(
            """SELECT COALESCE(NULLIF(e.area_tecnica_nome_aplicado, ''), a.nome, 'Sem área técnica') AS nome,
                      ROUND(AVG(e.pontuacao_final), 2) AS media, COUNT(*) AS quantidade
               FROM entrevistas e LEFT JOIN areas_tecnicas a ON a.id = e.area_tecnica_id
               WHERE e.status = 'avaliada' AND e.pontuacao_final BETWEEN 0 AND 10
                 AND e.data_fim >= ? AND e.data_fim < ?
               GROUP BY nome ORDER BY media DESC""", (desde, ate)
        )]
        dificuldades = [dict(linha) for linha in conexao.execute(
            """SELECT COALESCE(dificuldade, 'não classificada') AS nome, COUNT(*) AS quantidade
               FROM perguntas WHERE ativa = 1 GROUP BY nome ORDER BY quantidade DESC"""
        )]
        perguntas_por_tipo = [dict(linha) for linha in conexao.execute(
            """SELECT t.nome, COUNT(*) AS quantidade FROM perguntas p
               JOIN tipos_entrevista t ON t.id = p.tipo_entrevista_id
               WHERE p.ativa = 1 GROUP BY t.id ORDER BY quantidade DESC"""
        )]
        consumo_disponivel = _existe_tabela(conexao, "chamadas_openai")
        chamadas_hoje = _contar(
            conexao, "SELECT COUNT(*) FROM chamadas_openai WHERE dia_utc = ?", (hoje.isoformat(),)
        ) if consumo_disponivel else 0
        limite_global = _obter_limites()[1]
        ia = {
            "chamadas_hoje": chamadas_hoje, "limite_diario": limite_global,
            "registros_disponiveis": consumo_disponivel,
            "percentual": round(100 * chamadas_hoje / limite_global, 1),
            "erros_analise": entrevistas["erro_analise"]
        }
        cobertura = _cobertura_perguntas(conexao)
        recentes = [dict(linha) for linha in conexao.execute(
            """SELECT e.id, u.nome AS estudante,
                      COALESCE(NULLIF(e.tipo_entrevista_nome_aplicado, ''), t.nome) AS modalidade,
                      COALESCE(e.perfil_profissional, 'legado') AS perfil,
                      e.area_tecnica_nome_aplicado AS area, e.subarea_tecnica_nome_aplicado AS subarea,
                      e.status, e.data_inicio,
                      CASE WHEN e.status = 'avaliada' THEN e.pontuacao_final ELSE NULL END AS pontuacao_final
               FROM entrevistas e JOIN usuarios u ON u.id = e.usuario_id
               LEFT JOIN tipos_entrevista t ON t.id = e.tipo_entrevista_id
               ORDER BY e.data_inicio DESC, e.id DESC LIMIT 10"""
        )]
        # A lista de erros é independente das últimas dez entrevistas e do período filtrado.
        entrevistas_com_erro = [dict(linha) for linha in conexao.execute(
            """SELECT e.id, u.nome AS estudante,
                      COALESCE(NULLIF(e.tipo_entrevista_nome_aplicado, ''), t.nome) AS modalidade,
                      COALESCE(e.perfil_profissional, 'legado') AS perfil, e.data_inicio
               FROM entrevistas e JOIN usuarios u ON u.id = e.usuario_id
               LEFT JOIN tipos_entrevista t ON t.id = e.tipo_entrevista_id
               WHERE e.status = 'erro_analise' ORDER BY e.data_inicio DESC, e.id DESC LIMIT 50"""
        )]
        alertas = []
        if entrevistas["erro_analise"]:
            alertas.append({"titulo": "Erros na análise", "detalhe": f"{entrevistas['erro_analise']} entrevista(s) com erro de análise.", "gravidade": "alta"})
        if cobertura["total_pendentes"]:
            alertas.append({"titulo": "Cobertura insuficiente", "detalhe": f"{cobertura['total_pendentes']} combinação(ões) de modalidade, contexto e perfil sem oito perguntas válidas.", "gravidade": "alta"})
        if cadastros["sem_referencia"]:
            alertas.append({"titulo": "Perguntas sem referência", "detalhe": f"{cadastros['sem_referencia']} pergunta(s) ativa(s) sem resposta de referência.", "gravidade": "media"})
        if cadastros["soma_pesos_criterios"] > 1.000001:
            alertas.append({"titulo": "Pesos acima do limite", "detalhe": "A soma dos pesos dos critérios ativos ultrapassa 1,00.", "gravidade": "alta"})
        if ia["percentual"] >= 80:
            alertas.append({"titulo": "Cota da IA", "detalhe": f"Consumo diário em {ia['percentual']}% do limite global.", "gravidade": "media"})
        if entrevistas["finalizadas_pendentes"]:
            alertas.append({"titulo": "Avaliações pendentes", "detalhe": f"{entrevistas['finalizadas_pendentes']} entrevista(s) finalizada(s) aguardando solicitação de análise.", "gravidade": "informativa"})
        return {
            "periodo_dias": dias, "periodo_inicio": inicio.isoformat(), "periodo_fim": ultimo_dia.isoformat(), "cadastros": cadastros, "entrevistas": entrevistas,
            "serie": serie, "modalidades": modalidades, "perfis": perfis, "areas": areas,
            "medias_modalidades": medias_modalidades, "medias_areas": medias_areas,
            "dificuldades": dificuldades, "perguntas_por_tipo": perguntas_por_tipo,
            "ia": ia, "cobertura": cobertura, "alertas": alertas,
            "recentes": recentes, "entrevistas_com_erro": entrevistas_com_erro
        }
    finally:
        conexao.close()


@router.get("/entrevistas")
def listar_todas_entrevistas(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=15, ge=5, le=100),
    busca: str = Query(default="", max_length=120),
    situacao: Literal["em_andamento", "finalizada", "em_analise", "avaliada", "erro_analise", "cancelada"] | None = None,
    tipo_id: int | None = Query(default=None, gt=0),
    perfil: Literal["estagio_trainee", "junior", "pleno", "senior", "legado"] | None = None,
    area_id: int | None = Query(default=None, gt=0),
    data_de: date | None = None,
    data_ate: date | None = None,
    ordem: Literal["recentes", "antigas", "maior_nota", "menor_nota"] = "recentes",
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Lista todas as entrevistas com busca, filtros e paginação somente para administradores."""
    if data_de and data_ate and data_de > data_ate:
        raise HTTPException(status_code=422, detail="A data inicial não pode ser posterior à final.")

    condicoes, parametros = [], []
    texto = busca.strip()
    if texto:
        # Escapa curingas SQL para interpretar a pesquisa como texto literal.
        termo = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        condicoes.append("""(CAST(e.id AS TEXT) = ? OR u.nome LIKE ? ESCAPE '\\' COLLATE NOCASE
                         OR u.email LIKE ? ESCAPE '\\' COLLATE NOCASE
                         OR COALESCE(e.tipo_entrevista_nome_aplicado, t.nome, '') LIKE ? ESCAPE '\\' COLLATE NOCASE)""")
        parametros.extend((texto, f"%{termo}%", f"%{termo}%", f"%{termo}%"))
    if situacao:
        condicoes.append("e.status = ?")
        parametros.append(situacao)
    if tipo_id is not None:
        condicoes.append("e.tipo_entrevista_id = ?")
        parametros.append(tipo_id)
    if perfil:
        condicoes.append("COALESCE(e.perfil_profissional, 'legado') = ?")
        parametros.append(perfil)
    if area_id is not None:
        condicoes.append("e.area_tecnica_id = ?")
        parametros.append(area_id)
    if data_de:
        condicoes.append("SUBSTR(e.data_inicio, 1, 10) >= ?")
        parametros.append(data_de.isoformat())
    if data_ate:
        condicoes.append("SUBSTR(e.data_inicio, 1, 10) <= ?")
        parametros.append(data_ate.isoformat())

    tabelas = """FROM entrevistas e JOIN usuarios u ON u.id = e.usuario_id
                LEFT JOIN tipos_entrevista t ON t.id = e.tipo_entrevista_id"""
    onde = " WHERE " + " AND ".join(condicoes) if condicoes else ""
    ordenacoes = {
        "recentes": "e.data_inicio DESC, e.id DESC",
        "antigas": "e.data_inicio ASC, e.id ASC",
        "maior_nota": "CASE WHEN e.status = 'avaliada' AND e.pontuacao_final BETWEEN 0 AND 10 THEN 0 ELSE 1 END, e.pontuacao_final DESC, e.id DESC",
        "menor_nota": "CASE WHEN e.status = 'avaliada' AND e.pontuacao_final BETWEEN 0 AND 10 THEN 0 ELSE 1 END, e.pontuacao_final ASC, e.id DESC"
    }
    conexao = conectar_banco()
    try:
        total = _contar(conexao, "SELECT COUNT(*) " + tabelas + onde, tuple(parametros))
        paginas = max(1, (total + por_pagina - 1) // por_pagina)
        linhas = conexao.execute(
            """SELECT e.id, u.nome AS estudante,
                      COALESCE(NULLIF(e.tipo_entrevista_nome_aplicado, ''), t.nome, 'Tipo não identificado') AS modalidade,
                      COALESCE(e.perfil_profissional, 'legado') AS perfil,
                      e.area_tecnica_nome_aplicado AS area,
                      e.subarea_tecnica_nome_aplicado AS subarea,
                      e.status, e.data_inicio,
                      CASE WHEN e.status = 'avaliada' AND e.pontuacao_final BETWEEN 0 AND 10
                           THEN e.pontuacao_final ELSE NULL END AS pontuacao_final
               """ + tabelas + onde + " ORDER BY " + ordenacoes[ordem] + " LIMIT ? OFFSET ?",
            tuple(parametros + [por_pagina, (pagina - 1) * por_pagina])
        ).fetchall()
        tipos = [dict(linha) for linha in conexao.execute(
            """SELECT e.tipo_entrevista_id AS id,
                      COALESCE(MAX(NULLIF(e.tipo_entrevista_nome_aplicado, '')), MAX(t.nome), 'Tipo não identificado') AS nome
               FROM entrevistas e LEFT JOIN tipos_entrevista t ON t.id = e.tipo_entrevista_id
               GROUP BY e.tipo_entrevista_id ORDER BY nome, id"""
        )]
        areas = [dict(linha) for linha in conexao.execute(
            """SELECT e.area_tecnica_id AS id,
                      COALESCE(MAX(NULLIF(e.area_tecnica_nome_aplicado, '')), MAX(a.nome), 'Área não identificada') AS nome
               FROM entrevistas e LEFT JOIN areas_tecnicas a ON a.id = e.area_tecnica_id
               WHERE e.area_tecnica_id IS NOT NULL GROUP BY e.area_tecnica_id ORDER BY nome, id"""
        )]
        return {
            "itens": [dict(linha) for linha in linhas], "total": total,
            "pagina": pagina, "por_pagina": por_pagina, "total_paginas": paginas,
            "tipos": tipos, "areas": areas
        }
    finally:
        conexao.close()


@router.get("/entrevistas/{entrevista_id}")
def detalhe_entrevista_administrativa(
    entrevista_id: int = ParametroCaminho(gt=0),
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Diagnóstico somente de leitura, sem expor respostas ou dados internos da IA."""
    conexao = conectar_banco()
    try:
        registro = conexao.execute(
            """SELECT e.id, e.status, e.data_inicio, e.data_fim, e.perfil_profissional,
                      e.area_tecnica_nome_aplicado AS area, e.subarea_tecnica_nome_aplicado AS subarea,
                      COALESCE(NULLIF(e.tipo_entrevista_nome_aplicado, ''), t.nome) AS modalidade,
                      u.nome AS estudante,
                      (SELECT COUNT(*) FROM entrevista_perguntas p WHERE p.entrevista_id = e.id) AS perguntas,
                      (SELECT COUNT(*) FROM respostas r WHERE r.entrevista_id = e.id) AS respostas,
                      (SELECT COUNT(*) FROM avaliacoes a JOIN respostas r ON r.id = a.resposta_id
                       WHERE r.entrevista_id = e.id) AS avaliacoes
               FROM entrevistas e JOIN usuarios u ON u.id = e.usuario_id
               LEFT JOIN tipos_entrevista t ON t.id = e.tipo_entrevista_id
               WHERE e.id = ?""", (entrevista_id,)
        ).fetchone()
        if registro is None:
            raise HTTPException(status_code=404, detail="Entrevista não encontrada.")
        dados = dict(registro)
        limite_entrevista = _obter_limites()[2]
        total_chamadas = None
        if _existe_tabela(conexao, "consumo_entrevistas"):
            consumo = conexao.execute(
                "SELECT total_chamadas FROM consumo_entrevistas WHERE entrevista_id = ?", (entrevista_id,)
            ).fetchone()
            if consumo is not None:
                total_chamadas = consumo["total_chamadas"]
        if total_chamadas is None and _existe_tabela(conexao, "chamadas_openai"):
            # Um histórico purgado pode não conter todas as chamadas anteriores.
            total_chamadas = conexao.execute(
                "SELECT COUNT(*) FROM chamadas_openai WHERE entrevista_id = ?", (entrevista_id,)
            ).fetchone()[0]
        qtd = dados["respostas"]
        perfil_novo = dados["perfil_profissional"] is not None
        respostas_validas = 1 <= qtd <= 8 and (not perfil_novo or qtd == 8)
        orientacoes = []
        if not respostas_validas:
            orientacoes.append("A quantidade de respostas não atende às regras da análise. Verifique os dados antes de repetir.")
        if dados["avaliacoes"] > 0 and dados["status"] == "erro_analise":
            orientacoes.append("Há avaliações parciais. O serviço remove essas avaliações ao iniciar uma nova tentativa.")
        if total_chamadas is not None and total_chamadas >= limite_entrevista:
            orientacoes.append("O limite acumulado de chamadas desta entrevista pode impedir uma nova análise real.")
        if dados["status"] == "erro_analise":
            orientacoes.append("A causa específica desta falha não foi armazenada. Consulte os registros do backend no horário da tentativa.")
        if dados["status"] == "em_analise":
            orientacoes.append("A análise pode estar ativa; não inicie uma segunda execução. Use a rotina de recuperação após o prazo configurado.")
        if dados["status"] == "avaliada":
            orientacoes.append("A entrevista já foi avaliada; nenhuma nova análise é necessária.")
        dados.update({
            "chamadas_registradas": total_chamadas,
            "limite_chamadas_entrevista": limite_entrevista,
            "pode_solicitar_analise": dados["status"] == "erro_analise" and respostas_validas,
            "motivo_tecnico_registrado": None,
            "orientacoes": orientacoes
        })
        return dados
    finally:
        conexao.close()
