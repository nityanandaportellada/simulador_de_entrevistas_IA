
"""Funções responsáveis pela criação e pelo controle das entrevistas."""

import sqlite3
import random
import re
from datetime import datetime, timezone

try:
    from .database import conectar_banco
    from .models import Entrevista, EntrevistaPergunta
except ImportError:
    from database import conectar_banco
    from models import Entrevista, EntrevistaPergunta

PERFIS_PERGUNTAS = {
    "estagio_trainee": (5, 3, 0),
    "junior": (3, 4, 1),
    "pleno": (1, 4, 3),
    "senior": (0, 3, 5)
}
DIFICULDADES = ("basica", "intermediaria", "avancada")

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
    if type(valor) is not int or valor <= 0:
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
            p.codigo,
            p.dificuldade,
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
            p.codigo,
            p.dificuldade,
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
        LEFT JOIN competencias c ON c.id = p.competencia_id
        INNER JOIN areas_tecnicas a ON a.id = p.area_tecnica_id
        INNER JOIN subareas_tecnicas s ON s.id = p.subarea_tecnica_id
        WHERE p.tipo_entrevista_id = ?
          AND p.ativa = 1
          AND (p.competencia_id IS NULL OR c.ativa = 1)
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


def _selecionar_perguntas(perguntas, perfil_profissional: str, comportamental: bool):
    """Escolhe oito perguntas conforme o perfil e, se necessário, oito competências."""
    quantidades = PERFIS_PERGUNTAS[perfil_profissional]
    grupos = {nivel: [] for nivel in DIFICULDADES}
    nomes_competencias = {"comunicação", "trabalho em equipe", "resolução de problemas", "liderança", "adaptabilidade", "pensamento crítico", "organização", "tomada de decisão"}

    for pergunta in perguntas:
        if comportamental and (pergunta["competencia_nome"] or "").casefold() not in nomes_competencias:
            continue
        if pergunta["dificuldade"] in grupos:
            grupos[pergunta["dificuldade"]].append(pergunta)

    for nivel, quantidade in zip(DIFICULDADES, quantidades):
        if len(grupos[nivel]) < quantidade:
            raise ValueError(f"Não existem {quantidade} perguntas ativas de dificuldade {nivel} para este perfil.")
        random.shuffle(grupos[nivel])

    if not comportamental:
        escolhidas = []
        for nivel, quantidade in zip(DIFICULDADES, quantidades):
            escolhidas.extend(grupos[nivel][:quantidade])
        random.shuffle(escolhidas)
        return escolhidas

    # Para entrevistas comportamentais, cada competência aparece somente uma vez.
    competencias = {pergunta["competencia_id"] for grupo in grupos.values() for pergunta in grupo}

    if len(competencias) < 8:
        raise ValueError("São necessárias perguntas ativas de oito competências diferentes.")

    niveis = list(DIFICULDADES)
    restantes = dict(zip(DIFICULDADES, quantidades))
    escolhidas = []
    usadas = set()

    def escolher_proxima() -> bool:
        """Testa combinações simples até completar oito competências sem repetir."""
        if len(escolhidas) == 8:
            return True

        niveis_disponiveis = [nivel for nivel in niveis if restantes[nivel] > 0]
        random.shuffle(niveis_disponiveis)

        for nivel in niveis_disponiveis:
            for pergunta in grupos[nivel]:
                competencia_id = pergunta["competencia_id"]

                if competencia_id in usadas:
                    continue

                usadas.add(competencia_id)
                escolhidas.append(pergunta)
                restantes[nivel] -= 1

                if escolher_proxima():
                    return True

                restantes[nivel] += 1
                escolhidas.pop()
                usadas.remove(competencia_id)

        return False

    if not escolher_proxima():
        raise ValueError("Não há combinação suficiente de competências e dificuldades para este perfil.")

    random.shuffle(escolhidas)
    return escolhidas


def _selecionar_perguntas_lideranca(perguntas, perfil_profissional: str):
    """Escolhe oito perguntas de Liderança, uma de cada dimensão, conforme o perfil."""
    # O número final de cada código LID identifica a dimensão (01 a 08).
    grupos = {dimensao: {nivel: [] for nivel in DIFICULDADES} for dimensao in range(1, 9)}
    letras = {"B": "basica", "I": "intermediaria", "A": "avancada"}

    for pergunta in perguntas:
        codigo = pergunta["codigo"] or ""
        encontrado = re.fullmatch(r"LID-([BIA])(0[1-8])", codigo)
        if encontrado is None:
            continue
        nivel = letras[encontrado.group(1)]
        if pergunta["dificuldade"] == nivel:
            dimensao = int(encontrado.group(2))
            grupos[dimensao][nivel].append(pergunta)

    # A seleção não deve repetir uma dimensão para compensar outra ausente.
    for dimensao in grupos:
        if not any(grupos[dimensao][nivel] for nivel in DIFICULDADES):
            raise ValueError(f"Não existem perguntas ativas válidas para a dimensão de Liderança {dimensao:02d}.")
        for nivel in DIFICULDADES:
            random.shuffle(grupos[dimensao][nivel])

    restantes = dict(zip(DIFICULDADES, PERFIS_PERGUNTAS[perfil_profissional]))
    dimensoes = list(grupos)
    random.shuffle(dimensoes)
    escolhidas = []

    def escolher_proxima(indice: int) -> bool:
        """Procura uma combinação com uma dimensão por pergunta e as dificuldades exatas."""
        if indice == len(dimensoes):
            return all(quantidade == 0 for quantidade in restantes.values())

        dimensao = dimensoes[indice]
        niveis = [nivel for nivel in DIFICULDADES if restantes[nivel] > 0 and grupos[dimensao][nivel]]
        random.shuffle(niveis)

        for nivel in niveis:
            for pergunta in grupos[dimensao][nivel]:
                escolhidas.append(pergunta)
                restantes[nivel] -= 1
                if escolher_proxima(indice + 1):
                    return True
                restantes[nivel] += 1
                escolhidas.pop()
        return False

    if not escolher_proxima(0):
        raise ValueError("Não há combinação suficiente de dimensões e dificuldades para este perfil de Liderança.")

    random.shuffle(escolhidas)
    return escolhidas


def _congelar_perguntas(cursor: sqlite3.Cursor, entrevista_id: int, perguntas) -> None:
    """Copia oito perguntas distintas para o snapshot da entrevista."""
    if len(perguntas) != 8 or len({pergunta["id"] for pergunta in perguntas}) != 8:
        raise ValueError("A entrevista deve conter exatamente oito perguntas diferentes.")
    # Cada pergunta recebe um snapshot para que alterações futuras no catálogo não mudem a entrevista.
    for numero, pergunta in enumerate(perguntas, start=1):
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
                codigo_pergunta_aplicado,
                dificuldade_aplicada,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entrevista_id,
                pergunta["id"],
                pergunta["texto"],
                pergunta["exemplo_esperado"],
                pergunta["codigo"],
                pergunta["dificuldade"],
                pergunta["competencia_id"],
                pergunta["competencia_nome"],
                area_id,
                area_nome,
                subarea_id,
                subarea_nome,
                pergunta["peso"],
                1 if bool(pergunta["usa_star"]) else 0,
                numero if pergunta["dificuldade"] is not None else pergunta["ordem"]
            )
        )


def criar_entrevista(
    usuario_id: int,
    tipo_entrevista_id: int,
    area_tecnica_id: int | None = None,
    subarea_tecnica_id: int | None = None,
    perfil_profissional: str | None = None
) -> int:
    """Cria a entrevista com oito perguntas e perfil obrigatório em uma transação."""
    _validar_id(usuario_id, "Usuário")
    _validar_id(tipo_entrevista_id, "Tipo de entrevista")

    if perfil_profissional not in PERFIS_PERGUNTAS:
        raise ValueError("Selecione um perfil profissional válido antes de iniciar a entrevista.")

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

        # Em novas entrevistas, o perfil sempre define oito perguntas e a distribuição de níveis.
        nome_tipo = tipo["nome"].strip().casefold()
        if nome_tipo in ("liderança", "lideranca") and not bool(tipo["usa_area_tecnica"]):
            perguntas = _selecionar_perguntas_lideranca(perguntas, perfil_profissional)
        else:
            comportamental = nome_tipo == "comportamental"
            perguntas = _selecionar_perguntas(perguntas, perfil_profissional, comportamental)

        if len(perguntas) != 8 or len({pergunta["id"] for pergunta in perguntas}) != 8:
            raise ValueError("Não foi possível selecionar exatamente oito perguntas distintas.")

        quantidades_reais = tuple(sum(p["dificuldade"] == nivel for p in perguntas) for nivel in DIFICULDADES)

        if quantidades_reais != PERFIS_PERGUNTAS[perfil_profissional]:
            raise ValueError("A distribuição de dificuldades não corresponde ao perfil selecionado.")

        # Cria a entrevista. Os triggers do banco registram os snapshots do tipo e do contexto técnico.
        cursor.execute(
            """
            INSERT INTO entrevistas (
                usuario_id,
                tipo_entrevista_id,
                area_tecnica_id,
                subarea_tecnica_id,
                perfil_profissional,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'em_andamento')
            """,
            (
                usuario_id,
                tipo_entrevista_id,
                area_tecnica_id if area is not None else None,
                subarea_tecnica_id if subarea is not None else None,
                perfil_profissional
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

        if quantidade_congelada != 8:
            raise sqlite3.DatabaseError("Não foi possível congelar as oito perguntas da entrevista.")

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
    """Permite finalizar ou cancelar somente pelos serviços que validam a entrevista."""
    _validar_id(entrevista_id, "ID da entrevista")

    if novo_status == "finalizada":
        return finalizar_entrevista(entrevista_id)

    if novo_status == "cancelada":
        return cancelar_entrevista(entrevista_id)

    raise ValueError("A análise e a publicação de notas devem ser realizadas pelos serviços próprios.")


def finalizar_entrevista(entrevista_id: int) -> bool:
    """Finaliza a entrevista somente quando todas as perguntas congeladas foram respondidas."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A validação e a finalização usam a mesma transação para evitar condições de concorrência.
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT id, status, perfil_profissional FROM entrevistas WHERE id = ?",
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

        # Novas entrevistas precisam preservar as oito perguntas e as dificuldades do perfil.
        perfil = registro["perfil_profissional"]
        if perfil is not None:
            if perfil not in PERFIS_PERGUNTAS or quantidade_perguntas != 8:
                raise ValueError("A entrevista não possui as oito perguntas exigidas para o perfil.")

            cursor.execute(
                """
                SELECT dificuldade_aplicada, COUNT(*) AS quantidade
                FROM entrevista_perguntas WHERE entrevista_id = ?
                GROUP BY dificuldade_aplicada
                """,
                (entrevista_id,)
            )
            quantidades = {linha["dificuldade_aplicada"]: linha["quantidade"] for linha in cursor.fetchall()}
            esperado = dict(zip(DIFICULDADES, PERFIS_PERGUNTAS[perfil]))

            if any(quantidades.get(nivel, 0) != total for nivel, total in esperado.items()):
                raise ValueError("As dificuldades congeladas não correspondem ao perfil da entrevista.")

            cursor.execute(
                """
                SELECT COUNT(DISTINCT ordem_pergunta_aplicada) AS distintas,
                       MIN(ordem_pergunta_aplicada) AS menor, MAX(ordem_pergunta_aplicada) AS maior
                FROM entrevista_perguntas WHERE entrevista_id = ?
                """,
                (entrevista_id,)
            )
            ordem = cursor.fetchone()

            if ordem["distintas"] != 8 or ordem["menor"] != 1 or ordem["maior"] != 8:
                raise ValueError("A ordem das perguntas congeladas está inconsistente.")

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

            if perfil is not None:
                cursor.execute("SELECT COUNT(*) AS quantidade FROM respostas WHERE entrevista_id = ?", (entrevista_id,))
                if cursor.fetchone()["quantidade"] != quantidade_respostas:
                    raise ValueError("Existem respostas fora do conjunto congelado desta entrevista.")

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
    """Impede a publicação isolada de notas sem validar todas as avaliações."""
    _validar_id(entrevista_id, "ID da entrevista")

    if type(pontuacao) not in (int, float) or not 0 <= pontuacao <= 10:
        raise ValueError("A pontuação deve estar entre 0 e 10.")

    raise ValueError("A pontuação final deve ser publicada pelo serviço de avaliação.")


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
        ),
        perfil_profissional=registro["perfil_profissional"] if "perfil_profissional" in colunas else None
    )


def _registro_para_entrevista_pergunta(registro: sqlite3.Row) -> EntrevistaPergunta:
    """Transforma uma linha de entrevista_perguntas em um objeto EntrevistaPergunta."""
    colunas = registro.keys()

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
        data_aplicacao=registro["data_aplicacao"],
        codigo_pergunta_aplicado=registro["codigo_pergunta_aplicado"] if "codigo_pergunta_aplicado" in colunas else None,
        dificuldade_aplicada=registro["dificuldade_aplicada"] if "dificuldade_aplicada" in colunas else None
    )
