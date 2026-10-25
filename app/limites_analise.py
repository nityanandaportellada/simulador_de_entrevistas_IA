
"""Controla as cotas de chamadas reais à OpenAI e a retenção dos registros."""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

from .database import conectar_banco


class LimiteAnaliseError(ValueError):
    """Informa que uma cota foi atingida e quando tentar novamente, se aplicável."""
    def __init__(self, mensagem: str, tipo: str, retry_after: int | None = None):
        super().__init__(mensagem)
        self.tipo = tipo
        self.retry_after = retry_after


def _limite_configurado(nome: str, padrao: int, minimo: int = 1, maximo: int = 100000) -> int:
    """Lê um limite inteiro sem permitir valores inválidos ou desativação acidental."""
    texto = os.getenv(nome, str(padrao)).strip()
    if not texto.isascii() or not texto.isdecimal():
        raise RuntimeError(f"A configuração {nome} deve ser um inteiro positivo.")
    valor = int(texto)
    if not minimo <= valor <= maximo:
        raise RuntimeError(f"A configuração {nome} está fora do intervalo permitido.")
    return valor


# Configurações ajustáveis pelo administrador. Sem valores no banco, utiliza o .env.
CONFIGURACOES_IA = {
    "MAX_OPENAI_CALLS_USER_DAY": (32, 1, 100000),
    "MAX_OPENAI_CALLS_GLOBAL_DAY": (3200, 1, 100000),
    "MAX_OPENAI_CALLS_INTERVIEW": (24, 1, 100000),
    "OPENAI_LOG_RETENTION_DAYS": (90, 30, 365)
}


def _valores_efetivos(conexao: sqlite3.Connection | None = None) -> dict[str, int]:
    """Combina os valores do ambiente com substituições gravadas no SQLite."""
    valores = {chave: _limite_configurado(chave, *limites) for chave, limites in CONFIGURACOES_IA.items()}
    propria = conexao is None
    if propria:
        conexao = conectar_banco()
    try:
        existe = conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'configuracoes_ia'"
        ).fetchone()
        if existe:
            registros = conexao.execute("SELECT chave, valor FROM configuracoes_ia").fetchall()
            for registro in registros:
                chave, valor = registro["chave"], registro["valor"]
                if chave in CONFIGURACOES_IA:
                    padrao, minimo, maximo = CONFIGURACOES_IA[chave]
                    if type(valor) is not int or not minimo <= valor <= maximo:
                        raise RuntimeError(f"Valor inválido na configuração {chave}.")
                    valores[chave] = valor
    finally:
        if propria:
            conexao.close()
    return valores


def _obter_limites(conexao: sqlite3.Connection | None = None) -> tuple[int, int, int]:
    """Retorna as cotas reais: estudante/dia, global/dia e entrevista."""
    valores = _valores_efetivos(conexao)
    return (
        valores["MAX_OPENAI_CALLS_USER_DAY"],
        valores["MAX_OPENAI_CALLS_GLOBAL_DAY"],
        valores["MAX_OPENAI_CALLS_INTERVIEW"]
    )


def obter_configuracoes_ia() -> dict:
    """Lê os limites atuais e informa se há personalização no SQLite."""
    conexao = conectar_banco()
    try:
        valores = _valores_efetivos(conexao)
        existe = conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'configuracoes_ia'"
        ).fetchone()
        metadados = None
        personalizadas = False
        if existe:
            personalizadas = conexao.execute("SELECT 1 FROM configuracoes_ia LIMIT 1").fetchone() is not None
            metadados = conexao.execute(
                "SELECT alterado_em_utc, alterado_por FROM configuracoes_ia ORDER BY alterado_em_utc DESC LIMIT 1"
            ).fetchone()
        return {
            "limite_usuario_dia": valores["MAX_OPENAI_CALLS_USER_DAY"],
            "limite_global_dia": valores["MAX_OPENAI_CALLS_GLOBAL_DAY"],
            "limite_entrevista": valores["MAX_OPENAI_CALLS_INTERVIEW"],
            "retencao_dias": valores["OPENAI_LOG_RETENTION_DAYS"],
            "personalizada": personalizadas,
            "alterado_em_utc": metadados["alterado_em_utc"] if metadados else None,
            "alterado_por": metadados["alterado_por"] if metadados else None
        }
    finally:
        conexao.close()


def salvar_configuracoes_ia(limite_usuario_dia: int, limite_global_dia: int,
                             limite_entrevista: int, retencao_dias: int, administrador_id: int) -> dict:
    """Salva limites atomicamente sem reiniciar contadores de uso."""
    novos = {
        "MAX_OPENAI_CALLS_USER_DAY": limite_usuario_dia,
        "MAX_OPENAI_CALLS_GLOBAL_DAY": limite_global_dia,
        "MAX_OPENAI_CALLS_INTERVIEW": limite_entrevista,
        "OPENAI_LOG_RETENTION_DAYS": retencao_dias
    }
    for chave, valor in novos.items():
        _, minimo, maximo = CONFIGURACOES_IA[chave]
        if type(valor) is not int or not minimo <= valor <= maximo:
            raise ValueError(f"{chave}: informe um inteiro entre {minimo} e {maximo}.")
    if limite_usuario_dia > limite_global_dia:
        raise ValueError("O limite diário por estudante não pode ultrapassar o limite global diário.")
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes_ia (
                chave TEXT PRIMARY KEY,
                valor INTEGER NOT NULL CHECK(valor > 0),
                alterado_em_utc TEXT NOT NULL,
                alterado_por INTEGER NOT NULL
            )
        """)
        agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for chave, valor in novos.items():
            conexao.execute("""
                INSERT INTO configuracoes_ia (chave, valor, alterado_em_utc, alterado_por)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor,
                alterado_em_utc = excluded.alterado_em_utc, alterado_por = excluded.alterado_por
            """, (chave, valor, agora, administrador_id))
        # Uma mudança de retenção será considerada na próxima reserva.
        if conexao.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'controle_consumo_ia'"
        ).fetchone():
            conexao.execute("DELETE FROM controle_consumo_ia WHERE chave = 'ultima_limpeza'")
        conexao.commit()
        return obter_configuracoes_ia()
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _preparar_tabelas(conexao: sqlite3.Connection) -> None:
    """Prepara o histórico e migra somente uma vez os totais anteriores."""
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS chamadas_openai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            entrevista_id INTEGER NOT NULL,
            dia_utc TEXT NOT NULL,
            data_reserva_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_chamadas_openai_usuario_dia ON chamadas_openai(usuario_id, dia_utc)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_chamadas_openai_dia ON chamadas_openai(dia_utc)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_chamadas_openai_entrevista ON chamadas_openai(entrevista_id)")
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS consumo_entrevistas (
            entrevista_id INTEGER PRIMARY KEY,
            total_chamadas INTEGER NOT NULL DEFAULT 0 CHECK (total_chamadas >= 0)
        )
    """)
    conexao.execute("CREATE TABLE IF NOT EXISTS controle_consumo_ia (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)")
    migracao = conexao.execute(
        "SELECT valor FROM controle_consumo_ia WHERE chave = 'totais_v1'"
    ).fetchone()
    if migracao is None:
        # Preserva a cota acumulada das entrevistas já avaliadas antes deste lote.
        conexao.execute("""
            INSERT INTO consumo_entrevistas (entrevista_id, total_chamadas)
            SELECT entrevista_id, COUNT(*) FROM chamadas_openai GROUP BY entrevista_id
            ON CONFLICT(entrevista_id) DO UPDATE SET
                total_chamadas = MAX(total_chamadas, excluded.total_chamadas)
        """)
        conexao.execute("INSERT INTO controle_consumo_ia (chave, valor) VALUES ('totais_v1', 'ok')")


def _limpar_historico_antigo(conexao: sqlite3.Connection, hoje: str) -> None:
    """Elimina registros detalhados antigos, sem reiniciar os totais por entrevista."""
    ultima = conexao.execute(
        "SELECT valor FROM controle_consumo_ia WHERE chave = 'ultima_limpeza'"
    ).fetchone()
    if ultima is not None and ultima["valor"] == hoje:
        return
    dias = _valores_efetivos(conexao)["OPENAI_LOG_RETENTION_DAYS"]
    data_limite = (datetime.now(timezone.utc).date() - timedelta(days=dias)).isoformat()
    conexao.execute("DELETE FROM chamadas_openai WHERE dia_utc < ?", (data_limite,))
    conexao.execute("""
        INSERT INTO controle_consumo_ia (chave, valor) VALUES ('ultima_limpeza', ?)
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
    """, (hoje,))


def _segundos_ate_amanha() -> int:
    """Calcula o Retry-After das cotas diárias usando a virada do dia UTC."""
    agora = datetime.now(timezone.utc)
    amanha = datetime.combine(agora.date() + timedelta(days=1), datetime.min.time(), timezone.utc)
    return max(1, int((amanha - agora).total_seconds()) + 1)


def _checar_limites(conexao: sqlite3.Connection, usuario_id: int, entrevista_id: int, quantidade: int) -> None:
    """Confere as três cotas; o total por entrevista não depende da retenção."""
    limite_usuario, limite_global, limite_entrevista = _obter_limites(conexao)
    hoje = datetime.now(timezone.utc).date().isoformat()
    usuario_dia = conexao.execute(
        "SELECT COUNT(*) FROM chamadas_openai WHERE usuario_id = ? AND dia_utc = ?", (usuario_id, hoje)
    ).fetchone()[0]
    global_dia = conexao.execute(
        "SELECT COUNT(*) FROM chamadas_openai WHERE dia_utc = ?", (hoje,)
    ).fetchone()[0]
    registro = conexao.execute(
        "SELECT total_chamadas FROM consumo_entrevistas WHERE entrevista_id = ?", (entrevista_id,)
    ).fetchone()
    por_entrevista = registro["total_chamadas"] if registro else 0
    if usuario_dia + quantidade > limite_usuario:
        raise LimiteAnaliseError("Limite diário de avaliações por estudante atingido.", "usuario_diario", _segundos_ate_amanha())
    if global_dia + quantidade > limite_global:
        raise LimiteAnaliseError("O sistema atingiu o limite diário de avaliações pela IA.", "global_diario", _segundos_ate_amanha())
    if por_entrevista + quantidade > limite_entrevista:
        raise LimiteAnaliseError("Esta entrevista atingiu o limite acumulado de chamadas à IA.", "entrevista")


def verificar_saldo_analise(entrevista_id: int, quantidade: int) -> None:
    """Confere o saldo antes de iniciar a análise; não consome chamadas."""
    if type(entrevista_id) is not int or entrevista_id <= 0 or type(quantidade) is not int or quantidade <= 0:
        raise ValueError("Parâmetros de cota inválidos.")
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        _preparar_tabelas(conexao)
        registro = conexao.execute("SELECT usuario_id FROM entrevistas WHERE id = ?", (entrevista_id,)).fetchone()
        if registro is None:
            raise ValueError("Entrevista não encontrada.")
        _checar_limites(conexao, int(registro["usuario_id"]), entrevista_id, quantidade)
        conexao.commit()
    except (sqlite3.Error, ValueError, RuntimeError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def reservar_chamada_openai(entrevista_id: int) -> int:
    """Registra uma chamada antes de executá-la, sob transação exclusiva do SQLite."""
    if type(entrevista_id) is not int or entrevista_id <= 0:
        raise ValueError("ID da entrevista inválido.")
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        _preparar_tabelas(conexao)
        registro = conexao.execute(
            "SELECT usuario_id, status FROM entrevistas WHERE id = ?", (entrevista_id,)
        ).fetchone()
        if registro is None or registro["status"] != "em_analise":
            raise ValueError("A entrevista não está disponível para chamada à IA.")
        usuario_id = int(registro["usuario_id"])
        _checar_limites(conexao, usuario_id, entrevista_id, 1)
        hoje = datetime.now(timezone.utc).date().isoformat()
        cursor = conexao.execute(
            "INSERT INTO chamadas_openai (usuario_id, entrevista_id, dia_utc) VALUES (?, ?, ?)",
            (usuario_id, entrevista_id, hoje)
        )
        conexao.execute("""
            INSERT INTO consumo_entrevistas (entrevista_id, total_chamadas) VALUES (?, 1)
            ON CONFLICT(entrevista_id) DO UPDATE SET total_chamadas = total_chamadas + 1
        """, (entrevista_id,))
        _limpar_historico_antigo(conexao, hoje)
        conexao.commit()
        return int(cursor.lastrowid)
    except (sqlite3.Error, ValueError, RuntimeError):
        conexao.rollback()
        raise
    finally:
        conexao.close()
