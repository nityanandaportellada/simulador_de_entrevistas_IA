"""Funções responsáveis pela criação e pelo controle das entrevistas."""

import sqlite3
from datetime import datetime, timezone

try:
    from .database import conectar_banco
    from .models import Entrevista, EntrevistaPergunta
except ImportError:
    from database import conectar_banco
    from models import Entrevista, EntrevistaPergunta

STATUS_ENTREVISTA = (
    "em_andamento",
    "finalizada",
    "em_analise",
    "avaliada",
    "erro_analise",
    "cancelada"
)


def _agora_utc() -> str:
    """Retorna a data e a hora atual em UTC no formato usado pelo banco."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _validar_id(valor: int | None, campo: str) -> None:
    """Confere se um identificador foi informado e é maior que zero."""
    if valor is None or valor <= 0:
        raise ValueError(f"{campo} inválido.")


def _buscar_usuario_ativo(cursor: sqlite3.Cursor, usuario_id: int):
    """Busca um usuário ativo usando a mesma conexão da operação atual."""
    cursor.execute(
        """
        SELECT id, nome, email, perfil, ativo
        FROM usuarios
        WHERE id = ? AND ativo = 1
        """,
        (usuario_id,)
    )
    return cursor.fetchone()


def _buscar_tipo_entrevista_ativo(cursor: sqlite3.Cursor, tipo_entrevista_id: int):
    """Busca um tipo de entrevista ativo e informa se ele usa área técnica."""
    cursor.execute(
        """
        SELECT id, nome, descricao, ativo, usa_area_tecnica
        FROM tipos_entrevista
        WHERE id = ? AND ativo = 1
        """,
        (tipo_entrevista_id,)
    )
    return cursor.fetchone()


def _buscar_area_tecnica_ativa(cursor: sqlite3.Cursor, area_tecnica_id: int):
    """Busca uma área técnica ativa dentro da transação atual."""
    cursor.execute(
        """
        SELECT id, nome, descricao, ativo, ordem
        FROM areas_tecnicas
        WHERE id = ? AND ativo = 1
        """,
        (area_tecnica_id,)
    )
    return cursor.fetchone()


def _buscar_subarea_tecnica_ativa(cursor: sqlite3.Cursor, subarea_tecnica_id: int):
    """Busca uma subárea técnica ativa dentro da transação atual."""
    cursor.execute(
        """
        SELECT id, area_tecnica_id, nome, descricao, eh_geral, ativo, ordem
        FROM subareas_tecnicas
        WHERE id = ? AND ativo = 1
        """,
        (subarea_tecnica_id,)
    )
    return cursor.fetchone()


def _buscar_subarea_geral(cursor: sqlite3.Cursor, area_tecnica_id: int):
    """Busca a subárea Geral ativa que pertence à área informada."""
    cursor.execute(
        """
        SELECT id, area_tecnica_id, nome, descricao, eh_geral, ativo, ordem
        FROM subareas_tecnicas
        WHERE area_tecnica_id = ? AND eh_geral = 1 AND ativo = 1
        LIMIT 1
        """,
        (area_tecnica_id,)
    )
    return cursor.fetchone()


def _validar_contexto_area_tecnica(
    cursor: sqlite3.Cursor,
    tipo,
    area_tecnica_id: int | None,
    subarea_tecnica_id: int | None
):
    """Valida área e subárea conforme a configuração do tipo de entrevista."""
    usa_area_tecnica = bool(tipo["usa_area_tecnica"])

    # Tipos não técnicos não podem receber área ou subárea.
    if not usa_area_tecnica:
        if area_tecnica_id is not None or subarea_tecnica_id is not None:
            raise ValueError("Este tipo de entrevista não utiliza área ou subárea técnica.")
        return None, None, None

    # Tipos técnicos exigem os dois campos.
    if area_tecnica_id is None:
        raise ValueError("A área técnica é obrigatória para este tipo de entrevista.")

    if subarea_tecnica_id is None:
        raise ValueError("A subárea técnica é obrigatória para este tipo de entrevista.")

    _validar_id(area_tecnica_id, "Área técnica")
    _validar_id(subarea_tecnica_id, "Subárea técnica")

    # Confere se a área e a subárea estão ativas e relacionadas corretamente.
    area = _buscar_area_tecnica_ativa(cursor, area_tecnica_id)

    if area is None:
        raise ValueError("Área técnica não encontrada ou inativa.")

    subarea = _buscar_subarea_tecnica_ativa(cursor, subarea_tecnica_id)

    if subarea is None:
        raise ValueError("Subárea técnica não encontrada ou inativa.")

    if subarea["area_tecnica_id"] != area_tecnica_id:
        raise ValueError("A subárea informada não pertence à área técnica selecionada.")

    # Toda área técnica precisa ter uma subárea Geral ativa.
    subarea_geral = _buscar_subarea_geral(cursor, area_tecnica_id)

    if subarea_geral is None:
        raise ValueError("A área técnica selecionada não possui uma subárea Geral ativa.")

    return area, subarea, subarea_geral


def _buscar_perguntas_tipo_normal(cursor: sqlite3.Cursor, tipo_entrevista_id: int):
    """Busca perguntas ativas de um tipo que não utiliza área técnica."""
    cursor.execute(
        """
        SELECT
            p.id,
            p.tipo_entrevista_id,
            p.competencia_id,
            p.texto,
            p.exemplo_esperado,
            p.ordem,
            p.peso,
            p.usa_star,
            c.nome AS competencia_nome
        FROM perguntas p
        INNER JOIN competencias c ON c.id = p.competencia_id
        WHERE p.tipo_entrevista_id = ?
          AND p.ativa = 1
          AND c.ativa = 1
          AND p.area_tecnica_id IS NULL
          AND p.subarea_tecnica_id IS NULL
        ORDER BY COALESCE(p.ordem, 999999), p.id
        """,
        (tipo_entrevista_id,)
    )
    return cursor.fetchall()


def _buscar_perguntas_tipo_tecnico(
    cursor: sqlite3.Cursor,
    tipo_entrevista_id: int,
    area_tecnica_id: int,
    subarea_tecnica_id: int,
    subarea_geral_id: int
):
    """Busca perguntas técnicas da Geral e, quando necessário, da subárea escolhida."""
    # Se Geral foi escolhida, utiliza somente Geral. Caso contrário, usa Geral + específica.
    if subarea_tecnica_id == subarea_geral_id:
        subareas_ids = [subarea_geral_id]
    else:
        subareas_ids = [subarea_geral_id, subarea_tecnica_id]

    placeholders = ",".join("?" for _ in subareas_ids)
    parametros = [tipo_entrevista_id, area_tecnica_id, *subareas_ids]

    cursor.execute(
        f"""
        SELECT
            p.id,
            p.tipo_entrevista_id,
            p.competencia_id,
            p.texto,
            p.exemplo_esperado,
            p.ordem,
            p.peso,
            p.usa_star,
            p.area_tecnica_id,
            p.subarea_tecnica_id,
            c.nome AS competencia_nome,
            a.nome AS area_tecnica_nome,
            s.nome AS subarea_tecnica_nome,
            s.eh_geral AS subarea_eh_geral
        FROM perguntas p
        INNER JOIN competencias c ON c.id = p.competencia_id
        INNER JOIN areas_tecnicas a ON a.id = p.area_tecnica_id
        INNER JOIN subareas_tecnicas s ON s.id = p.subarea_tecnica_id
        WHERE p.tipo_entrevista_id = ?
          AND p.ativa = 1
          AND c.ativa = 1
          AND a.ativo = 1
          AND s.ativo = 1
          AND p.area_tecnica_id = ?
          AND p.subarea_tecnica_id IN ({placeholders})
          AND s.area_tecnica_id = p.area_tecnica_id
        ORDER BY
            CASE WHEN s.eh_geral = 1 THEN 0 ELSE 1 END,
            COALESCE(p.ordem, 999999),
            p.id
        """,
        tuple(parametros)
    )
    return cursor.fetchall()


def _congelar_perguntas(cursor: sqlite3.Cursor, entrevista_id: int, perguntas) -> None:
    """Copia para entrevista_perguntas exatamente os dados usados no início da entrevista."""
    # Cada pergunta recebe um snapshot para que alterações futuras no catálogo não mudem a entrevista.
    for pergunta in perguntas:
        colunas = pergunta.keys()
        area_id = pergunta["area_tecnica_id"] if "area_tecnica_id" in colunas else None
        area_nome = pergunta["area_tecnica_nome"] if "area_tecnica_nome" in colunas else None
        subarea_id = pergunta["subarea_tecnica_id"] if "subarea_tecnica_id" in colunas else None
        subarea_nome = pergunta["subarea_tecnica_nome"] if "subarea_tecnica_nome" in colunas else None

        cursor.execute(
            """
            INSERT INTO entrevista_perguntas (
                entrevista_id,
                pergunta_id,
                pergunta_texto_aplicado,
                exemplo_esperado_aplicado,
                competencia_id_aplicada,
                competencia_nome_aplicada,
                area_tecnica_id_aplicada,
                area_tecnica_nome_aplicada,
                subarea_tecnica_id_aplicada,
                subarea_tecnica_nome_aplicada,
                peso_pergunta_aplicado,
                usa_star_aplicado,
                ordem_pergunta_aplicada
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entrevista_id,
                pergunta["id"],
                pergunta["texto"],
                pergunta["exemplo_esperado"],
                pergunta["competencia_id"],
                pergunta["competencia_nome"],
                area_id,
                area_nome,
                subarea_id,
                subarea_nome,
                pergunta["peso"],
                1 if bool(pergunta["usa_star"]) else 0,
                pergunta["ordem"]
            )
        )


def criar_entrevista(
    usuario_id: int,
    tipo_entrevista_id: int,
    area_tecnica_id: int | None = None,
    subarea_tecnica_id: int | None = None
) -> int:
    """Cria a entrevista e congela suas perguntas na mesma transação."""
    _validar_id(usuario_id, "Usuário")
    _validar_id(tipo_entrevista_id, "Tipo de entrevista")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A transação evita que a entrevista seja criada sem todas as perguntas congeladas.
        cursor.execute("BEGIN IMMEDIATE")

        usuario = _buscar_usuario_ativo(cursor, usuario_id)

        if usuario is None:
            raise ValueError("Usuário não encontrado ou inativo.")

        tipo = _buscar_tipo_entrevista_ativo(cursor, tipo_entrevista_id)

        if tipo is None:
            raise ValueError("Tipo de entrevista não encontrado ou inativo.")

        area, subarea, subarea_geral = _validar_contexto_area_tecnica(
            cursor,
            tipo,
            area_tecnica_id,
            subarea_tecnica_id
        )

        # Seleciona as perguntas conforme o tipo configurado no banco.
        if bool(tipo["usa_area_tecnica"]):
            perguntas = _buscar_perguntas_tipo_tecnico(
                cursor=cursor,
                tipo_entrevista_id=tipo_entrevista_id,
                area_tecnica_id=area_tecnica_id,
                subarea_tecnica_id=subarea_tecnica_id,
                subarea_geral_id=subarea_geral["id"]
            )
        else:
            perguntas = _buscar_perguntas_tipo_normal(cursor, tipo_entrevista_id)

        if not perguntas:
            if bool(tipo["usa_area_tecnica"]):
                raise ValueError("Não existem perguntas ativas disponíveis para a área e subárea selecionadas.")
            raise ValueError("Não existem perguntas ativas disponíveis para este tipo de entrevista.")

        # Cria a entrevista. Os triggers do banco registram os snapshots do tipo e do contexto técnico.
        cursor.execute(
            """
            INSERT INTO entrevistas (
                usuario_id,
                tipo_entrevista_id,
                area_tecnica_id,
                subarea_tecnica_id,
                status
            )
            VALUES (?, ?, ?, ?, 'em_andamento')
            """,
            (
                usuario_id,
                tipo_entrevista_id,
                area_tecnica_id if area is not None else None,
                subarea_tecnica_id if subarea is not None else None
            )
        )
        entrevista_id = int(cursor.lastrowid)

        # Congela as perguntas escolhidas e confirma se todas foram gravadas.
        _congelar_perguntas(cursor, entrevista_id, perguntas)

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM entrevista_perguntas
            WHERE entrevista_id = ?
            """,
            (entrevista_id,)
        )
        quantidade_congelada = int(cursor.fetchone()["quantidade"])

        if quantidade_congelada != len(perguntas):
            raise sqlite3.DatabaseError("Não foi possível congelar corretamente todas as perguntas da entrevista.")

        conexao.commit()
        return entrevista_id

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def buscar_entrevista(entrevista_id: int) -> Entrevista | None:
    """Busca uma entrevista pelo ID e devolve None quando ela não existe."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("SELECT * FROM entrevistas WHERE id = ?", (entrevista_id,))
        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_entrevista(registro)
    finally:
        conexao.close()


def listar_entrevistas_usuario(usuario_id: int) -> list[Entrevista]:
    """Lista as entrevistas de um usuário, mostrando primeiro as mais recentes."""
    _validar_id(usuario_id, "Usuário")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT *
            FROM entrevistas
            WHERE usuario_id = ?
            ORDER BY data_inicio DESC, id DESC
            """,
            (usuario_id,)
        )
        registros = cursor.fetchall()
        return [_registro_para_entrevista(registro) for registro in registros]
    finally:
        conexao.close()


def listar_entrevistas() -> list[Entrevista]:
    """Lista todas as entrevistas, principalmente para consultas administrativas."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT *
            FROM entrevistas
            ORDER BY data_inicio DESC, id DESC
            """
        )
        registros = cursor.fetchall()
        return [_registro_para_entrevista(registro) for registro in registros]
    finally:
        conexao.close()


def listar_perguntas_entrevista(entrevista_id: int) -> list[EntrevistaPergunta]:
    """Retorna exatamente as perguntas congeladas quando a entrevista foi criada."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Primeiro confirma que a entrevista existe.
        cursor.execute("SELECT id FROM entrevistas WHERE id = ?", (entrevista_id,))

        if cursor.fetchone() is None:
            raise ValueError("Entrevista não encontrada.")

        # Usa somente entrevista_perguntas para preservar o conjunto histórico.
        cursor.execute(
            """
            SELECT *
            FROM entrevista_perguntas
            WHERE entrevista_id = ?
            ORDER BY COALESCE(ordem_pergunta_aplicada, 999999), id
            """,
            (entrevista_id,)
        )
        registros = cursor.fetchall()
        return [_registro_para_entrevista_pergunta(registro) for registro in registros]
    finally:
        conexao.close()


def buscar_pergunta_entrevista(entrevista_id: int, pergunta_id: int) -> EntrevistaPergunta | None:
    """Verifica se uma pergunta pertence ao conjunto congelado da entrevista."""
    _validar_id(entrevista_id, "ID da entrevista")
    _validar_id(pergunta_id, "ID da pergunta")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT *
            FROM entrevista_perguntas
            WHERE entrevista_id = ? AND pergunta_id = ?
            LIMIT 1
            """,
            (entrevista_id, pergunta_id)
        )
        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_entrevista_pergunta(registro)
    finally:
        conexao.close()


def contar_perguntas_entrevista(entrevista_id: int) -> int:
    """Retorna quantas perguntas foram congeladas para a entrevista."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM entrevista_perguntas
            WHERE entrevista_id = ?
            """,
            (entrevista_id,)
        )
        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def alterar_status_entrevista(entrevista_id: int, novo_status: str) -> bool:
    """Altera o status da entrevista quando o novo valor é permitido pelo sistema."""
    _validar_id(entrevista_id, "ID da entrevista")

    if novo_status not in STATUS_ENTREVISTA:
        raise ValueError(f"Status de entrevista inválido: {novo_status}")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "UPDATE entrevistas SET status = ? WHERE id = ?",
            (novo_status, entrevista_id)
        )
        alterada = cursor.rowcount > 0
        conexao.commit()
        return alterada
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def finalizar_entrevista(entrevista_id: int) -> bool:
    """Finaliza a entrevista somente quando todas as perguntas congeladas foram respondidas."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A validação e a finalização usam a mesma transação para evitar condições de concorrência.
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT id, status FROM entrevistas WHERE id = ?",
            (entrevista_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            raise ValueError("Entrevista não encontrada.")

        if registro["status"] != "em_andamento":
            raise ValueError("Somente entrevistas em andamento podem ser finalizadas.")

        # Entrevistas atuais usam entrevista_perguntas como conjunto oficial.
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM entrevista_perguntas
            WHERE entrevista_id = ?
            """,
            (entrevista_id,)
        )
        quantidade_perguntas = int(cursor.fetchone()["quantidade"])

        if quantidade_perguntas > 0:
            # Conta somente respostas que pertencem ao conjunto congelado da entrevista.
            cursor.execute(
                """
                SELECT COUNT(DISTINCT r.pergunta_id) AS quantidade
                FROM respostas r
                INNER JOIN entrevista_perguntas ep
                    ON ep.entrevista_id = r.entrevista_id
                   AND ep.pergunta_id = r.pergunta_id
                WHERE r.entrevista_id = ?
                """,
                (entrevista_id,)
            )
            quantidade_respostas = int(cursor.fetchone()["quantidade"])
            quantidade_pendentes = max(0, quantidade_perguntas - quantidade_respostas)

            if quantidade_pendentes > 0:
                raise ValueError(
                    "A entrevista não pode ser finalizada enquanto houver perguntas sem resposta. "
                    f"Perguntas: {quantidade_perguntas}; respostas: {quantidade_respostas}; "
                    f"pendentes: {quantidade_pendentes}."
                )
        else:
            # Compatibilidade com entrevistas antigas que não possuem conjunto congelado.
            cursor.execute(
                "SELECT COUNT(*) AS quantidade FROM respostas WHERE entrevista_id = ?",
                (entrevista_id,)
            )
            quantidade_respostas = int(cursor.fetchone()["quantidade"])

            if quantidade_respostas <= 0:
                raise ValueError("A entrevista não pode ser finalizada sem respostas.")

        cursor.execute(
            """
            UPDATE entrevistas
            SET status = 'finalizada', data_fim = ?
            WHERE id = ? AND status = 'em_andamento'
            """,
            (_agora_utc(), entrevista_id)
        )

        if cursor.rowcount <= 0:
            raise ValueError("Não foi possível finalizar a entrevista.")

        conexao.commit()
        return True

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def cancelar_entrevista(entrevista_id: int) -> bool:
    """Cancela uma entrevista somente quando ela ainda está em andamento."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT id, status FROM entrevistas WHERE id = ?",
            (entrevista_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            raise ValueError("Entrevista não encontrada.")

        if registro["status"] != "em_andamento":
            raise ValueError("Somente entrevistas em andamento podem ser canceladas.")

        cursor.execute(
            """
            UPDATE entrevistas
            SET status = 'cancelada', data_fim = ?
            WHERE id = ?
            """,
            (_agora_utc(), entrevista_id)
        )
        alterada = cursor.rowcount > 0
        conexao.commit()
        return alterada

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def registrar_pontuacao_final(entrevista_id: int, pontuacao: float) -> bool:
    """Registra a pontuação final da entrevista usando a escala de 0 a 10."""
    _validar_id(entrevista_id, "ID da entrevista")

    if pontuacao < 0 or pontuacao > 10:
        raise ValueError("A pontuação deve estar entre 0 e 10.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "UPDATE entrevistas SET pontuacao_final = ? WHERE id = ?",
            (pontuacao, entrevista_id)
        )
        alterada = cursor.rowcount > 0
        conexao.commit()
        return alterada
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def contar_respostas(entrevista_id: int) -> int:
    """Retorna a quantidade de respostas registradas para a entrevista."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "SELECT COUNT(*) AS quantidade FROM respostas WHERE entrevista_id = ?",
            (entrevista_id,)
        )
        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def _registro_para_entrevista(registro: sqlite3.Row) -> Entrevista:
    """Transforma uma linha do SQLite em um objeto Entrevista."""
    colunas = registro.keys()

    return Entrevista(
        id=registro["id"],
        usuario_id=registro["usuario_id"],
        tipo_entrevista_id=registro["tipo_entrevista_id"],
        data_inicio=registro["data_inicio"],
        data_fim=registro["data_fim"],
        status=registro["status"],
        pontuacao_final=registro["pontuacao_final"],
        observacoes=registro["observacoes"],
        tipo_entrevista_nome_aplicado=(
            registro["tipo_entrevista_nome_aplicado"]
            if "tipo_entrevista_nome_aplicado" in colunas else None
        ),
        tipo_entrevista_descricao_aplicada=(
            registro["tipo_entrevista_descricao_aplicada"]
            if "tipo_entrevista_descricao_aplicada" in colunas else None
        ),
        area_tecnica_id=registro["area_tecnica_id"] if "area_tecnica_id" in colunas else None,
        subarea_tecnica_id=registro["subarea_tecnica_id"] if "subarea_tecnica_id" in colunas else None,
        area_tecnica_nome_aplicado=(
            registro["area_tecnica_nome_aplicado"]
            if "area_tecnica_nome_aplicado" in colunas else None
        ),
        subarea_tecnica_nome_aplicado=(
            registro["subarea_tecnica_nome_aplicado"]
            if "subarea_tecnica_nome_aplicado" in colunas else None
        )
    )


def _registro_para_entrevista_pergunta(registro: sqlite3.Row) -> EntrevistaPergunta:
    """Transforma uma linha de entrevista_perguntas em um objeto EntrevistaPergunta."""
    return EntrevistaPergunta(
        id=registro["id"],
        entrevista_id=registro["entrevista_id"],
        pergunta_id=registro["pergunta_id"],
        pergunta_texto_aplicado=registro["pergunta_texto_aplicado"],
        exemplo_esperado_aplicado=registro["exemplo_esperado_aplicado"],
        competencia_id_aplicada=registro["competencia_id_aplicada"],
        competencia_nome_aplicada=registro["competencia_nome_aplicada"],
        area_tecnica_id_aplicada=registro["area_tecnica_id_aplicada"],
        area_tecnica_nome_aplicada=registro["area_tecnica_nome_aplicada"],
        subarea_tecnica_id_aplicada=registro["subarea_tecnica_id_aplicada"],
        subarea_tecnica_nome_aplicada=registro["subarea_tecnica_nome_aplicada"],
        peso_pergunta_aplicado=registro["peso_pergunta_aplicado"],
        usa_star_aplicado=bool(registro["usa_star_aplicado"]),
        ordem_pergunta_aplicada=registro["ordem_pergunta_aplicada"],
        data_aplicacao=registro["data_aplicacao"]
    )