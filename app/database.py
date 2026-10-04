"""
database.py

Responsável pela conexão com o banco de dados SQLite
e pela criação das tabelas do Simulador de Entrevistas.

Versão: 0.5

Nesta versão são preservados historicamente:

1. Peso utilizado nos critérios de avaliação.

2. Dados da pergunta utilizada em cada resposta.

3. Nome e descrição do tipo de entrevista utilizado.

4. Nome, descrição, ordem e peso dos critérios
   utilizados em cada avaliação.

SNAPSHOT DE CRITÉRIO:

    avaliacao_criterios.criterio_nome_aplicado
    avaliacao_criterios.criterio_descricao_aplicada
    avaliacao_criterios.criterio_ordem_aplicada
    avaliacao_criterios.peso_aplicado

SNAPSHOT DE PERGUNTA:

    respostas.pergunta_texto_aplicado
    respostas.exemplo_esperado_aplicado
    respostas.competencia_id_aplicada
    respostas.competencia_nome_aplicada
    respostas.peso_pergunta_aplicado
    respostas.usa_star_aplicado
    respostas.ordem_pergunta_aplicada

SNAPSHOT DO TIPO DE ENTREVISTA:

    entrevistas.tipo_entrevista_nome_aplicado
    entrevistas.tipo_entrevista_descricao_aplicada

A finalidade dos snapshots é impedir que alterações
administrativas futuras modifiquem entrevistas,
avaliações ou relatórios históricos.
"""

import os
import sqlite3


# ============================================================
# CONFIGURAÇÃO DO BANCO
# ============================================================

PASTA_BANCO = "data"

NOME_BANCO = "entrevistas.db"

CAMINHO_BANCO = os.path.join(
    PASTA_BANCO,
    NOME_BANCO
)


# ============================================================
# CONEXÃO
# ============================================================

def conectar_banco():
    """
    Cria e retorna uma conexão com o SQLite.

    Também:

    - cria a pasta do banco;
    - permite acessar colunas pelo nome;
    - ativa chaves estrangeiras.
    """

    os.makedirs(
        PASTA_BANCO,
        exist_ok=True
    )

    conexao = sqlite3.connect(
        CAMINHO_BANCO
    )

    conexao.row_factory = sqlite3.Row

    conexao.execute(
        "PRAGMA foreign_keys = ON;"
    )

    return conexao


# ============================================================
# VERIFICAR COLUNA
# ============================================================

def _coluna_existe(
    cursor: sqlite3.Cursor,
    tabela: str,
    coluna: str
) -> bool:
    """
    Verifica se uma coluna existe em determinada tabela.
    """

    cursor.execute(
        f"PRAGMA table_info({tabela})"
    )

    colunas = cursor.fetchall()

    return any(
        registro["name"] == coluna
        for registro in colunas
    )


# ============================================================
# ADICIONAR COLUNA
# ============================================================

def _adicionar_coluna(
    cursor: sqlite3.Cursor,
    tabela: str,
    coluna: str,
    definicao: str
) -> None:
    """
    Adiciona uma coluna somente quando ela ainda não existe.
    """

    if _coluna_existe(
        cursor,
        tabela,
        coluna
    ):

        return

    cursor.execute(
        f"""
        ALTER TABLE {tabela}

        ADD COLUMN {coluna} {definicao}
        """
    )


# ============================================================
# MIGRAÇÃO DO PESO HISTÓRICO DO CRITÉRIO
# ============================================================

def _migrar_peso_aplicado(
    cursor: sqlite3.Cursor
) -> None:
    """
    Garante a existência do peso histórico
    utilizado em cada avaliação por critério.
    """

    _adicionar_coluna(
        cursor,
        "avaliacao_criterios",
        "peso_aplicado",
        """
        REAL
        CHECK (
            peso_aplicado IS NULL
            OR peso_aplicado >= 0
        )
        """
    )

    cursor.execute(
        """
        UPDATE avaliacao_criterios

        SET peso_aplicado = (
            SELECT ca.peso

            FROM criterios_avaliacao ca

            WHERE ca.id =
                avaliacao_criterios.criterio_id
        )

        WHERE peso_aplicado IS NULL
        """
    )

    cursor.execute(
        """
        SELECT COUNT(*) AS quantidade

        FROM avaliacao_criterios

        WHERE peso_aplicado IS NULL
        """
    )

    quantidade = int(
        cursor.fetchone()["quantidade"]
    )

    if quantidade > 0:

        raise sqlite3.IntegrityError(
            "Existem avaliações por critério "
            "sem peso histórico."
        )


# ============================================================
# MIGRAÇÃO DOS METADADOS DOS CRITÉRIOS
# ============================================================

def _migrar_snapshot_criterios(
    cursor: sqlite3.Cursor
) -> None:
    """
    Adiciona e preenche os metadados históricos
    de cada critério utilizado em uma avaliação.

    Para avaliações anteriores à versão 0.5,
    utiliza os valores administrativos atuais como
    melhor informação histórica disponível.
    """

    _adicionar_coluna(
        cursor,
        "avaliacao_criterios",
        "criterio_nome_aplicado",
        "TEXT"
    )

    _adicionar_coluna(
        cursor,
        "avaliacao_criterios",
        "criterio_descricao_aplicada",
        "TEXT"
    )

    _adicionar_coluna(
        cursor,
        "avaliacao_criterios",
        "criterio_ordem_aplicada",
        "INTEGER"
    )

    cursor.execute(
        """
        UPDATE avaliacao_criterios

        SET

            criterio_nome_aplicado = (
                SELECT ca.nome

                FROM criterios_avaliacao ca

                WHERE ca.id =
                    avaliacao_criterios.criterio_id
            ),

            criterio_descricao_aplicada = (
                SELECT ca.descricao

                FROM criterios_avaliacao ca

                WHERE ca.id =
                    avaliacao_criterios.criterio_id
            ),

            criterio_ordem_aplicada = (
                SELECT ca.ordem

                FROM criterios_avaliacao ca

                WHERE ca.id =
                    avaliacao_criterios.criterio_id
            )

        WHERE criterio_nome_aplicado IS NULL
        """
    )

    cursor.execute(
        """
        SELECT COUNT(*) AS quantidade

        FROM avaliacao_criterios

        WHERE criterio_nome_aplicado IS NULL
        """
    )

    quantidade = int(
        cursor.fetchone()["quantidade"]
    )

    if quantidade > 0:

        raise sqlite3.IntegrityError(
            "Existem avaliações sem snapshot "
            "histórico do critério."
        )


# ============================================================
# TRIGGERS DO SNAPSHOT DOS CRITÉRIOS
# ============================================================

def _criar_triggers_snapshot_criterios(
    cursor: sqlite3.Cursor
) -> None:
    """
    Cria triggers responsáveis por:

    - capturar peso e metadados do critério;
    - impedir alterações posteriores.
    """

    # --------------------------------------------------------
    # PESO
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_avaliacao_criterios_peso_insert

        AFTER INSERT ON avaliacao_criterios

        FOR EACH ROW

        WHEN NEW.peso_aplicado IS NULL

        BEGIN

            UPDATE avaliacao_criterios

            SET peso_aplicado = (
                SELECT peso

                FROM criterios_avaliacao

                WHERE id = NEW.criterio_id
            )

            WHERE id = NEW.id;


            SELECT CASE

                WHEN (
                    SELECT peso_aplicado

                    FROM avaliacao_criterios

                    WHERE id = NEW.id
                ) IS NULL

                THEN RAISE(
                    ABORT,
                    'Não foi possível registrar o peso histórico do critério.'
                )

            END;

        END;
        """
    )

    # --------------------------------------------------------
    # METADADOS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_avaliacao_criterios_snapshot_insert

        AFTER INSERT ON avaliacao_criterios

        FOR EACH ROW

        WHEN NEW.criterio_nome_aplicado IS NULL

        BEGIN

            UPDATE avaliacao_criterios

            SET

                criterio_nome_aplicado = (
                    SELECT nome

                    FROM criterios_avaliacao

                    WHERE id = NEW.criterio_id
                ),

                criterio_descricao_aplicada = (
                    SELECT descricao

                    FROM criterios_avaliacao

                    WHERE id = NEW.criterio_id
                ),

                criterio_ordem_aplicada = (
                    SELECT ordem

                    FROM criterios_avaliacao

                    WHERE id = NEW.criterio_id
                )

            WHERE id = NEW.id;


            SELECT CASE

                WHEN (
                    SELECT criterio_nome_aplicado

                    FROM avaliacao_criterios

                    WHERE id = NEW.id
                ) IS NULL

                THEN RAISE(
                    ABORT,
                    'Não foi possível registrar o snapshot histórico do critério.'
                )

            END;

        END;
        """
    )

    # --------------------------------------------------------
    # PESO IMUTÁVEL
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_avaliacao_criterios_peso_imutavel

        BEFORE UPDATE OF peso_aplicado
        ON avaliacao_criterios

        FOR EACH ROW

        WHEN
            OLD.peso_aplicado IS NOT NULL

            AND NEW.peso_aplicado
                IS NOT OLD.peso_aplicado

        BEGIN

            SELECT RAISE(
                ABORT,
                'O peso histórico da avaliação não pode ser alterado.'
            );

        END;
        """
    )

    # --------------------------------------------------------
    # METADADOS IMUTÁVEIS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_avaliacao_criterios_snapshot_imutavel

        BEFORE UPDATE OF

            criterio_nome_aplicado,
            criterio_descricao_aplicada,
            criterio_ordem_aplicada

        ON avaliacao_criterios

        FOR EACH ROW

        WHEN

            OLD.criterio_nome_aplicado IS NOT NULL

            AND (

                NEW.criterio_nome_aplicado
                    IS NOT OLD.criterio_nome_aplicado

                OR NEW.criterio_descricao_aplicada
                    IS NOT OLD.criterio_descricao_aplicada

                OR NEW.criterio_ordem_aplicada
                    IS NOT OLD.criterio_ordem_aplicada

            )

        BEGIN

            SELECT RAISE(
                ABORT,
                'O snapshot histórico do critério não pode ser alterado.'
            );

        END;
        """
    )


# ============================================================
# MIGRAÇÃO DO SNAPSHOT DAS PERGUNTAS
# ============================================================

def _migrar_snapshot_perguntas(
    cursor: sqlite3.Cursor
) -> None:
    """
    Adiciona e preenche o snapshot histórico
    das perguntas utilizadas nas respostas.
    """

    _adicionar_coluna(
        cursor,
        "respostas",
        "pergunta_texto_aplicado",
        "TEXT"
    )

    _adicionar_coluna(
        cursor,
        "respostas",
        "exemplo_esperado_aplicado",
        "TEXT"
    )

    _adicionar_coluna(
        cursor,
        "respostas",
        "competencia_id_aplicada",
        "INTEGER"
    )

    _adicionar_coluna(
        cursor,
        "respostas",
        "competencia_nome_aplicada",
        "TEXT"
    )

    _adicionar_coluna(
        cursor,
        "respostas",
        "peso_pergunta_aplicado",
        """
        REAL
        CHECK (
            peso_pergunta_aplicado IS NULL
            OR peso_pergunta_aplicado >= 0
        )
        """
    )

    _adicionar_coluna(
        cursor,
        "respostas",
        "usa_star_aplicado",
        """
        INTEGER
        CHECK (
            usa_star_aplicado IS NULL
            OR usa_star_aplicado IN (0, 1)
        )
        """
    )

    _adicionar_coluna(
        cursor,
        "respostas",
        "ordem_pergunta_aplicada",
        "INTEGER"
    )

    cursor.execute(
        """
        UPDATE respostas

        SET

            pergunta_texto_aplicado = (
                SELECT p.texto

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id
            ),

            exemplo_esperado_aplicado = (
                SELECT p.exemplo_esperado

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id
            ),

            competencia_id_aplicada = (
                SELECT p.competencia_id

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id
            ),

            competencia_nome_aplicada = (
                SELECT c.nome

                FROM perguntas p

                INNER JOIN competencias c
                    ON c.id = p.competencia_id

                WHERE p.id =
                    respostas.pergunta_id
            ),

            peso_pergunta_aplicado = (
                SELECT p.peso

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id
            ),

            usa_star_aplicado = (
                SELECT p.usa_star

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id
            ),

            ordem_pergunta_aplicada = (
                SELECT p.ordem

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id
            )

        WHERE peso_pergunta_aplicado IS NULL
        """
    )

    cursor.execute(
        """
        SELECT COUNT(*) AS quantidade

        FROM respostas

        WHERE pergunta_texto_aplicado IS NULL

           OR competencia_id_aplicada IS NULL

           OR competencia_nome_aplicada IS NULL

           OR peso_pergunta_aplicado IS NULL

           OR usa_star_aplicado IS NULL
        """
    )

    quantidade = int(
        cursor.fetchone()["quantidade"]
    )

    if quantidade > 0:

        raise sqlite3.IntegrityError(
            "Existem respostas sem snapshot "
            "histórico completo da pergunta."
        )


# ============================================================
# TRIGGERS DO SNAPSHOT DAS PERGUNTAS
# ============================================================

def _criar_triggers_snapshot_pergunta(
    cursor: sqlite3.Cursor
) -> None:
    """
    Cria triggers responsáveis por preservar
    historicamente as perguntas utilizadas.
    """

    # --------------------------------------------------------
    # IMPEDIR SNAPSHOT MANUAL
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_respostas_snapshot_insert_protegido

        BEFORE INSERT ON respostas

        FOR EACH ROW

        WHEN
            NEW.pergunta_texto_aplicado IS NOT NULL

            OR NEW.exemplo_esperado_aplicado IS NOT NULL

            OR NEW.competencia_id_aplicada IS NOT NULL

            OR NEW.competencia_nome_aplicada IS NOT NULL

            OR NEW.peso_pergunta_aplicado IS NOT NULL

            OR NEW.usa_star_aplicado IS NOT NULL

            OR NEW.ordem_pergunta_aplicada IS NOT NULL

        BEGIN

            SELECT RAISE(
                ABORT,
                'O snapshot histórico da pergunta é preenchido automaticamente.'
            );

        END;
        """
    )

    # --------------------------------------------------------
    # CAPTURAR SNAPSHOT
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_respostas_snapshot_insert

        AFTER INSERT ON respostas

        FOR EACH ROW

        WHEN NEW.peso_pergunta_aplicado IS NULL

        BEGIN

            UPDATE respostas

            SET

                pergunta_texto_aplicado = (
                    SELECT p.texto

                    FROM perguntas p

                    WHERE p.id = NEW.pergunta_id
                ),

                exemplo_esperado_aplicado = (
                    SELECT p.exemplo_esperado

                    FROM perguntas p

                    WHERE p.id = NEW.pergunta_id
                ),

                competencia_id_aplicada = (
                    SELECT p.competencia_id

                    FROM perguntas p

                    WHERE p.id = NEW.pergunta_id
                ),

                competencia_nome_aplicada = (
                    SELECT c.nome

                    FROM perguntas p

                    INNER JOIN competencias c
                        ON c.id = p.competencia_id

                    WHERE p.id = NEW.pergunta_id
                ),

                peso_pergunta_aplicado = (
                    SELECT p.peso

                    FROM perguntas p

                    WHERE p.id = NEW.pergunta_id
                ),

                usa_star_aplicado = (
                    SELECT p.usa_star

                    FROM perguntas p

                    WHERE p.id = NEW.pergunta_id
                ),

                ordem_pergunta_aplicada = (
                    SELECT p.ordem

                    FROM perguntas p

                    WHERE p.id = NEW.pergunta_id
                )

            WHERE id = NEW.id;


            SELECT CASE

                WHEN (
                    SELECT pergunta_texto_aplicado

                    FROM respostas

                    WHERE id = NEW.id
                ) IS NULL

                THEN RAISE(
                    ABORT,
                    'Não foi possível registrar o texto histórico da pergunta.'
                )

            END;


            SELECT CASE

                WHEN (
                    SELECT competencia_id_aplicada

                    FROM respostas

                    WHERE id = NEW.id
                ) IS NULL

                THEN RAISE(
                    ABORT,
                    'Não foi possível registrar a competência histórica da pergunta.'
                )

            END;


            SELECT CASE

                WHEN (
                    SELECT competencia_nome_aplicada

                    FROM respostas

                    WHERE id = NEW.id
                ) IS NULL

                THEN RAISE(
                    ABORT,
                    'Não foi possível registrar o nome histórico da competência.'
                )

            END;


            SELECT CASE

                WHEN (
                    SELECT peso_pergunta_aplicado

                    FROM respostas

                    WHERE id = NEW.id
                ) IS NULL

                THEN RAISE(
                    ABORT,
                    'Não foi possível registrar o peso histórico da pergunta.'
                )

            END;


            SELECT CASE

                WHEN (
                    SELECT usa_star_aplicado

                    FROM respostas

                    WHERE id = NEW.id
                ) IS NULL

                THEN RAISE(
                    ABORT,
                    'Não foi possível registrar o STAR histórico da pergunta.'
                )

            END;

        END;
        """
    )

    # --------------------------------------------------------
    # IMUTABILIDADE
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_respostas_snapshot_imutavel

        BEFORE UPDATE OF

            pergunta_texto_aplicado,
            exemplo_esperado_aplicado,
            competencia_id_aplicada,
            competencia_nome_aplicada,
            peso_pergunta_aplicado,
            usa_star_aplicado,
            ordem_pergunta_aplicada

        ON respostas

        FOR EACH ROW

        WHEN

            OLD.peso_pergunta_aplicado IS NOT NULL

            AND (

                NEW.pergunta_texto_aplicado
                    IS NOT OLD.pergunta_texto_aplicado

                OR NEW.exemplo_esperado_aplicado
                    IS NOT OLD.exemplo_esperado_aplicado

                OR NEW.competencia_id_aplicada
                    IS NOT OLD.competencia_id_aplicada

                OR NEW.competencia_nome_aplicada
                    IS NOT OLD.competencia_nome_aplicada

                OR NEW.peso_pergunta_aplicado
                    IS NOT OLD.peso_pergunta_aplicado

                OR NEW.usa_star_aplicado
                    IS NOT OLD.usa_star_aplicado

                OR NEW.ordem_pergunta_aplicada
                    IS NOT OLD.ordem_pergunta_aplicada

            )

        BEGIN

            SELECT RAISE(
                ABORT,
                'O snapshot histórico da pergunta não pode ser alterado.'
            );

        END;
        """
    )


# ============================================================
# MIGRAÇÃO DO TIPO DE ENTREVISTA
# ============================================================

def _migrar_snapshot_tipo_entrevista(
    cursor: sqlite3.Cursor
) -> None:
    """
    Adiciona e preenche o snapshot histórico
    do tipo de entrevista utilizado.
    """

    _adicionar_coluna(
        cursor,
        "entrevistas",
        "tipo_entrevista_nome_aplicado",
        "TEXT"
    )

    _adicionar_coluna(
        cursor,
        "entrevistas",
        "tipo_entrevista_descricao_aplicada",
        "TEXT"
    )

    cursor.execute(
        """
        UPDATE entrevistas

        SET

            tipo_entrevista_nome_aplicado = (
                SELECT te.nome

                FROM tipos_entrevista te

                WHERE te.id =
                    entrevistas.tipo_entrevista_id
            ),

            tipo_entrevista_descricao_aplicada = (
                SELECT te.descricao

                FROM tipos_entrevista te

                WHERE te.id =
                    entrevistas.tipo_entrevista_id
            )

        WHERE tipo_entrevista_nome_aplicado IS NULL
        """
    )

    cursor.execute(
        """
        SELECT COUNT(*) AS quantidade

        FROM entrevistas

        WHERE tipo_entrevista_nome_aplicado IS NULL
        """
    )

    quantidade = int(
        cursor.fetchone()["quantidade"]
    )

    if quantidade > 0:

        raise sqlite3.IntegrityError(
            "Existem entrevistas sem snapshot "
            "histórico do tipo de entrevista."
        )


# ============================================================
# TRIGGERS DO TIPO DE ENTREVISTA
# ============================================================

def _criar_triggers_snapshot_tipo_entrevista(
    cursor: sqlite3.Cursor
) -> None:
    """
    Captura e protege o nome e a descrição
    do tipo de entrevista.
    """

    # --------------------------------------------------------
    # CAPTURAR SNAPSHOT
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_entrevistas_tipo_snapshot_insert

        AFTER INSERT ON entrevistas

        FOR EACH ROW

        WHEN NEW.tipo_entrevista_nome_aplicado IS NULL

        BEGIN

            UPDATE entrevistas

            SET

                tipo_entrevista_nome_aplicado = (
                    SELECT nome

                    FROM tipos_entrevista

                    WHERE id =
                        NEW.tipo_entrevista_id
                ),

                tipo_entrevista_descricao_aplicada = (
                    SELECT descricao

                    FROM tipos_entrevista

                    WHERE id =
                        NEW.tipo_entrevista_id
                )

            WHERE id = NEW.id;


            SELECT CASE

                WHEN (
                    SELECT tipo_entrevista_nome_aplicado

                    FROM entrevistas

                    WHERE id = NEW.id
                ) IS NULL

                THEN RAISE(
                    ABORT,
                    'Não foi possível registrar o tipo histórico da entrevista.'
                )

            END;

        END;
        """
    )

    # --------------------------------------------------------
    # IMUTABILIDADE
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS
            trg_entrevistas_tipo_snapshot_imutavel

        BEFORE UPDATE OF

            tipo_entrevista_nome_aplicado,
            tipo_entrevista_descricao_aplicada

        ON entrevistas

        FOR EACH ROW

        WHEN

            OLD.tipo_entrevista_nome_aplicado IS NOT NULL

            AND (

                NEW.tipo_entrevista_nome_aplicado
                    IS NOT OLD.tipo_entrevista_nome_aplicado

                OR NEW.tipo_entrevista_descricao_aplicada
                    IS NOT OLD.tipo_entrevista_descricao_aplicada

            )

        BEGIN

            SELECT RAISE(
                ABORT,
                'O snapshot histórico do tipo de entrevista não pode ser alterado.'
            );

        END;
        """
    )


# ============================================================
# CRIAR TABELAS
# ============================================================

def criar_tabelas():
    """
    Cria e migra a estrutura completa do banco.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()

    try:

        # ====================================================
        # USUÁRIOS
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                nome TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,

                senha_hash TEXT NOT NULL,

                perfil TEXT NOT NULL
                    DEFAULT 'estudante'
                    CHECK (
                        perfil IN (
                            'estudante',
                            'administrador'
                        )
                    ),

                ativo INTEGER NOT NULL
                    DEFAULT 1
                    CHECK (
                        ativo IN (0, 1)
                    ),

                data_criacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                ultimo_acesso DATETIME

            );
            """
        )


        # ====================================================
        # TIPOS DE ENTREVISTA
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tipos_entrevista (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                nome TEXT NOT NULL UNIQUE,

                descricao TEXT,

                ativo INTEGER NOT NULL
                    DEFAULT 1
                    CHECK (
                        ativo IN (0, 1)
                    ),

                data_criacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP

            );
            """
        )


        # ====================================================
        # COMPETÊNCIAS
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS competencias (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                nome TEXT NOT NULL UNIQUE,

                descricao TEXT,

                ativa INTEGER NOT NULL
                    DEFAULT 1
                    CHECK (
                        ativa IN (0, 1)
                    )

            );
            """
        )


        # ====================================================
        # CRITÉRIOS
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS criterios_avaliacao (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                nome TEXT NOT NULL UNIQUE,

                descricao TEXT,

                peso REAL NOT NULL
                    DEFAULT 1.0
                    CHECK (
                        peso >= 0
                    ),

                ordem INTEGER,

                ativo INTEGER NOT NULL
                    DEFAULT 1
                    CHECK (
                        ativo IN (0, 1)
                    )

            );
            """
        )


        # ====================================================
        # PERGUNTAS
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS perguntas (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                tipo_entrevista_id INTEGER NOT NULL,

                competencia_id INTEGER NOT NULL,

                texto TEXT NOT NULL,

                exemplo_esperado TEXT,

                ordem INTEGER,

                ativa INTEGER NOT NULL
                    DEFAULT 1
                    CHECK (
                        ativa IN (0, 1)
                    ),

                peso REAL NOT NULL
                    DEFAULT 1.0
                    CHECK (
                        peso >= 0
                    ),

                usa_star INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (
                        usa_star IN (0, 1)
                    ),

                data_criacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    tipo_entrevista_id
                )
                REFERENCES tipos_entrevista(id),

                FOREIGN KEY (
                    competencia_id
                )
                REFERENCES competencias(id)

            );
            """
        )


        # ====================================================
        # ENTREVISTAS
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entrevistas (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                usuario_id INTEGER NOT NULL,

                tipo_entrevista_id INTEGER NOT NULL,

                data_inicio DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                data_fim DATETIME,

                status TEXT NOT NULL
                    DEFAULT 'em_andamento'
                    CHECK (
                        status IN (
                            'em_andamento',
                            'finalizada',
                            'em_analise',
                            'avaliada',
                            'erro_analise',
                            'cancelada'
                        )
                    ),

                pontuacao_final REAL,

                observacoes TEXT,

                tipo_entrevista_nome_aplicado TEXT,

                tipo_entrevista_descricao_aplicada TEXT,

                FOREIGN KEY (
                    usuario_id
                )
                REFERENCES usuarios(id),

                FOREIGN KEY (
                    tipo_entrevista_id
                )
                REFERENCES tipos_entrevista(id)

            );
            """
        )


        # ====================================================
        # RESPOSTAS
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS respostas (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                entrevista_id INTEGER NOT NULL,

                pergunta_id INTEGER NOT NULL,

                texto_resposta TEXT NOT NULL,

                tempo_resposta INTEGER
                    CHECK (
                        tempo_resposta IS NULL
                        OR tempo_resposta >= 0
                    ),

                data_resposta DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                pergunta_texto_aplicado TEXT,

                exemplo_esperado_aplicado TEXT,

                competencia_id_aplicada INTEGER,

                competencia_nome_aplicada TEXT,

                peso_pergunta_aplicado REAL
                    CHECK (
                        peso_pergunta_aplicado IS NULL
                        OR peso_pergunta_aplicado >= 0
                    ),

                usa_star_aplicado INTEGER
                    CHECK (
                        usa_star_aplicado IS NULL
                        OR usa_star_aplicado IN (0, 1)
                    ),

                ordem_pergunta_aplicada INTEGER,

                FOREIGN KEY (
                    entrevista_id
                )
                REFERENCES entrevistas(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    pergunta_id
                )
                REFERENCES perguntas(id),

                UNIQUE (
                    entrevista_id,
                    pergunta_id
                )

            );
            """
        )


        # ====================================================
        # AVALIAÇÕES
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS avaliacoes (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                resposta_id INTEGER NOT NULL UNIQUE,

                pontuacao REAL
                    CHECK (
                        pontuacao IS NULL
                        OR (
                            pontuacao >= 0
                            AND pontuacao <= 10
                        )
                    ),

                pontos_fortes TEXT,

                pontos_melhoria TEXT,

                feedback TEXT,

                modelo_ia TEXT,

                data_avaliacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    resposta_id
                )
                REFERENCES respostas(id)
                ON DELETE CASCADE

            );
            """
        )


        # ====================================================
        # AVALIAÇÃO POR CRITÉRIO
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS avaliacao_criterios (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                avaliacao_id INTEGER NOT NULL,

                criterio_id INTEGER NOT NULL,

                nota REAL NOT NULL
                    CHECK (
                        nota >= 0
                        AND nota <= 10
                    ),

                observacao TEXT,

                peso_aplicado REAL
                    CHECK (
                        peso_aplicado IS NULL
                        OR peso_aplicado >= 0
                    ),

                criterio_nome_aplicado TEXT,

                criterio_descricao_aplicada TEXT,

                criterio_ordem_aplicada INTEGER,

                FOREIGN KEY (
                    avaliacao_id
                )
                REFERENCES avaliacoes(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    criterio_id
                )
                REFERENCES criterios_avaliacao(id),

                UNIQUE (
                    avaliacao_id,
                    criterio_id
                )

            );
            """
        )


        # ====================================================
        # MIGRAÇÕES
        # ====================================================

        _migrar_peso_aplicado(
            cursor
        )

        _migrar_snapshot_criterios(
            cursor
        )

        _migrar_snapshot_perguntas(
            cursor
        )

        _migrar_snapshot_tipo_entrevista(
            cursor
        )


        # ====================================================
        # TRIGGERS
        # ====================================================

        _criar_triggers_snapshot_criterios(
            cursor
        )

        _criar_triggers_snapshot_pergunta(
            cursor
        )

        _criar_triggers_snapshot_tipo_entrevista(
            cursor
        )


        # ====================================================
        # HISTÓRICO DE ACESSO
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS historico_acesso (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                usuario_id INTEGER NOT NULL,

                acao TEXT NOT NULL,

                descricao TEXT,

                data_acao DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                ip TEXT,

                FOREIGN KEY (
                    usuario_id
                )
                REFERENCES usuarios(id)

            );
            """
        )


        # ====================================================
        # CONFIGURAÇÕES
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracoes (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                chave TEXT NOT NULL UNIQUE,

                valor TEXT,

                descricao TEXT,

                data_atualizacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP

            );
            """
        )


        # ====================================================
        # ÍNDICES
        # ====================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_perguntas_tipo

            ON perguntas (
                tipo_entrevista_id
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_perguntas_competencia

            ON perguntas (
                competencia_id
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_entrevistas_usuario

            ON entrevistas (
                usuario_id
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_respostas_entrevista

            ON respostas (
                entrevista_id
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_avaliacao_criterios_avaliacao

            ON avaliacao_criterios (
                avaliacao_id
            );
            """
        )


        # ====================================================
        # FINALIZAR
        # ====================================================

        conexao.commit()

        print(
            "Banco de dados versão 0.5 "
            "criado/atualizado com sucesso."
        )


    except (
        sqlite3.Error,
        ValueError
    ) as erro:

        conexao.rollback()

        print(
            f"Erro ao criar/atualizar "
            f"o banco de dados: {erro}"
        )

        raise


    finally:

        conexao.close()


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    criar_tabelas()