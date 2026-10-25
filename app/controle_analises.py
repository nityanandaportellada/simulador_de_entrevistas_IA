
"""Registra análises iniciadas pela API e recupera execuções interrompidas."""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

from .database import conectar_banco


class AnaliseEmAndamentoError(ValueError):
    """Indica que outra requisição controla a análise desta entrevista."""


def _validar_id(entrevista_id: int) -> None:
    if type(entrevista_id) is not int or entrevista_id <= 0:
        raise ValueError("ID da entrevista inválido.")


def _preparar_tabela(conexao: sqlite3.Connection) -> None:
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS analises_monitoradas (
            entrevista_id INTEGER PRIMARY KEY,
            inicio_utc TEXT NOT NULL
        )
    """)


def _prazo_recuperacao() -> timedelta:
    """Define um prazo conservador, superior às oito chamadas usuais da API."""
    texto = os.getenv("ANALISE_RECUPERACAO_MINUTOS", "90").strip()
    if not texto.isascii() or not texto.isdecimal() or not 30 <= int(texto) <= 1440:
        raise RuntimeError("ANALISE_RECUPERACAO_MINUTOS deve estar entre 30 e 1440.")
    return timedelta(minutes=int(texto))


def _expirou(inicio_utc: str) -> bool:
    """Verifica se a execução ultrapassou o limite sem conclusão registrada."""
    try:
        inicio = datetime.fromisoformat(inicio_utc)
    except ValueError as erro:
        raise RuntimeError("Data de monitoramento de análise inválida.") from erro
    if inicio.tzinfo is None:
        raise RuntimeError("Data de monitoramento sem fuso horário.")
    return datetime.now(timezone.utc) - inicio >= _prazo_recuperacao()


def recuperar_analise_interrompida(entrevista_id: int) -> bool:
    """Marca uma análise vencida como erro e remove somente avaliações parciais."""
    _validar_id(entrevista_id)
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        _preparar_tabela(conexao)
        registro = conexao.execute(
            "SELECT inicio_utc FROM analises_monitoradas WHERE entrevista_id = ?", (entrevista_id,)
        ).fetchone()
        if registro is None or not _expirou(registro["inicio_utc"]):
            conexao.commit()
            return False
        entrevista = conexao.execute(
            "SELECT status FROM entrevistas WHERE id = ?", (entrevista_id,)
        ).fetchone()
        recuperada = False
        if entrevista is not None and entrevista["status"] == "em_analise":
            # O status precisa mudar antes das exclusões por causa dos triggers de integridade.
            conexao.execute("""
                UPDATE entrevistas SET status = 'erro_analise', pontuacao_final = NULL
                WHERE id = ? AND status = 'em_analise'
            """, (entrevista_id,))
            conexao.execute("""
                DELETE FROM avaliacao_criterios WHERE avaliacao_id IN (
                    SELECT a.id FROM avaliacoes a INNER JOIN respostas r ON r.id = a.resposta_id
                    WHERE r.entrevista_id = ?
                )
            """, (entrevista_id,))
            conexao.execute("""
                DELETE FROM avaliacoes WHERE resposta_id IN (
                    SELECT id FROM respostas WHERE entrevista_id = ?
                )
            """, (entrevista_id,))
            recuperada = True
        # Se a execução terminou normalmente, remove somente o monitoramento vencido.
        conexao.execute("DELETE FROM analises_monitoradas WHERE entrevista_id = ?", (entrevista_id,))
        conexao.commit()
        return recuperada
    except (sqlite3.Error, ValueError, RuntimeError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def registrar_inicio_analise(entrevista_id: int) -> None:
    """Impede duas requisições simultâneas antes mesmo da reserva da IA."""
    _validar_id(entrevista_id)
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        _preparar_tabela(conexao)
        entrevista = conexao.execute("SELECT status FROM entrevistas WHERE id = ?", (entrevista_id,)).fetchone()
        if entrevista is None or entrevista["status"] not in ("finalizada", "erro_analise"):
            raise ValueError("A entrevista não está disponível para análise.")
        existente = conexao.execute(
            "SELECT inicio_utc FROM analises_monitoradas WHERE entrevista_id = ?", (entrevista_id,)
        ).fetchone()
        if existente is not None:
            if not _expirou(existente["inicio_utc"]):
                raise AnaliseEmAndamentoError("A análise desta entrevista já foi solicitada.")
            # Uma reserva abandonada antes do início efetivo pode ser liberada após o prazo.
            conexao.execute("DELETE FROM analises_monitoradas WHERE entrevista_id = ?", (entrevista_id,))
        inicio = datetime.now(timezone.utc).isoformat()
        conexao.execute(
            "INSERT INTO analises_monitoradas (entrevista_id, inicio_utc) VALUES (?, ?)",
            (entrevista_id, inicio)
        )
        conexao.commit()
    except (sqlite3.Error, ValueError, RuntimeError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def finalizar_monitoramento(entrevista_id: int) -> None:
    """Libera a reserva, mas mantém o registro se a análise ainda estiver pendente."""
    _validar_id(entrevista_id)
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        entrevista = conexao.execute(
            "SELECT status FROM entrevistas WHERE id = ?", (entrevista_id,)
        ).fetchone()
        # Se a limpeza da análise falhar, o monitoramento deve sobreviver à requisição.
        if entrevista is None or entrevista["status"] != "em_analise":
            conexao.execute("DELETE FROM analises_monitoradas WHERE entrevista_id = ?", (entrevista_id,))
        conexao.commit()
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()
