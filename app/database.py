"""
database.py

Responsável pela conexão com o banco de dados SQLite
e pela criação/evolução das tabelas do Simulador de Entrevistas.

Versão: 0.6

Principais recursos preservados nesta versão:

- usuários e perfis;
- tipos de entrevista;
- competências;
- critérios dinâmicos de avaliação;
- perguntas;
- entrevistas;
- respostas;
- avaliações;
- histórico de acesso;
- snapshots históricos de perguntas, tipos e critérios.

Novos recursos desta versão:

- áreas técnicas;
- subáreas técnicas;
- configuração do tipo de entrevista que utiliza área técnica;
- associação opcional de perguntas a área/subárea;
- associação opcional de entrevistas a área/subárea;
- snapshots históricos de área/subárea;
- tabela entrevista_perguntas para congelar o conjunto de perguntas
  aplicado no início de uma entrevista.
"""

import os
import sqlite3


# ============================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================

PASTA_BANCO = "data"

NOME_BANCO = "entrevistas.db"

CAMINHO_BANCO = os.path.join(
    PASTA_BANCO,
    NOME_BANCO
)


# ============================================================
# ÁREAS TÉCNICAS INICIAIS
# ============================================================

AREAS_TECNICAS_INICIAIS = (

    (
        "Direito",

        "Área destinada a entrevistas técnicas relacionadas "
        "ao campo jurídico.",

        1
    ),

    (
        "Psicologia",

        "Área destinada a entrevistas técnicas relacionadas "
        "à Psicologia.",

        2
    ),

    (
        "Administração",

        "Área destinada a entrevistas técnicas relacionadas "
        "à Administração.",

        3
    ),

    (
        "Economia",

        "Área destinada a entrevistas técnicas relacionadas "
        "à Economia.",

        4
    ),

    (
        "Ciências Contábeis",

        "Área destinada a entrevistas técnicas relacionadas "
        "às Ciências Contábeis.",

        5
    ),

    (
        "Tecnologia",

        "Área destinada a entrevistas técnicas relacionadas "
        "à Tecnologia e áreas correlatas.",

        6
    )

)


# ============================================================
# CONEXÃO COM O BANCO
# ============================================================

def conectar_banco():
    """
    Cria e retorna uma conexão com o banco SQLite.

    A função também:

    - cria a pasta do banco caso ela não exista;
    - permite acessar as colunas pelo nome;
    - ativa o suporte às chaves estrangeiras.
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
# FUNÇÕES AUXILIARES DE EVOLUÇÃO DO BANCO
# ============================================================

def _colunas_tabela(
    cursor: sqlite3.Cursor,
    tabela: str
) -> set[str]:
    """
    Retorna os nomes das colunas existentes em uma tabela.
    """

    cursor.execute(
        f"PRAGMA table_info({tabela})"
    )

    return {

        registro["name"]

        for registro
        in cursor.fetchall()

    }


def _adicionar_coluna_se_ausente(
    cursor: sqlite3.Cursor,
    tabela: str,
    coluna: str,
    definicao: str
) -> None:
    """
    Adiciona uma coluna somente quando ela ainda não existe.

    Essa função permite atualizar bancos já existentes sem
    apagar os dados armazenados.
    """

    if coluna in _colunas_tabela(
        cursor,
        tabela
    ):

        return

    cursor.execute(
        f"""
        ALTER TABLE {tabela}

        ADD COLUMN {coluna} {definicao}
        """
    )


# ============================================================
# CRIAÇÃO DAS TABELAS
# ============================================================

def criar_tabelas():
    """
    Cria as tabelas necessárias e evolui estruturas antigas.

    CREATE TABLE IF NOT EXISTS preserva bancos já existentes.

    Para colunas adicionadas após as primeiras versões do
    projeto são utilizadas alterações controladas de schema.
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
                        ativo IN (
                            0,
                            1
                        )
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
                        ativo IN (
                            0,
                            1
                        )
                    ),

                data_criacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                usa_area_tecnica INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (
                        usa_area_tecnica IN (
                            0,
                            1
                        )
                    )

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
                        ativa IN (
                            0,
                            1
                        )
                    )

            );
            """
        )


        # ====================================================
        # CRITÉRIOS DE AVALIAÇÃO
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
                        ativo IN (
                            0,
                            1
                        )
                    )

            );
            """
        )


        # ====================================================
        # ÁREAS TÉCNICAS
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS areas_tecnicas (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                nome TEXT NOT NULL
                    COLLATE NOCASE
                    UNIQUE,

                descricao TEXT,

                ativo INTEGER NOT NULL
                    DEFAULT 1
                    CHECK (
                        ativo IN (
                            0,
                            1
                        )
                    ),

                ordem INTEGER,

                data_criacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP

            );
            """
        )


        # ====================================================
        # SUBÁREAS TÉCNICAS
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subareas_tecnicas (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                area_tecnica_id INTEGER NOT NULL,

                nome TEXT NOT NULL
                    COLLATE NOCASE,

                descricao TEXT,

                eh_geral INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (
                        eh_geral IN (
                            0,
                            1
                        )
                    ),

                ativo INTEGER NOT NULL
                    DEFAULT 1
                    CHECK (
                        ativo IN (
                            0,
                            1
                        )
                    ),

                ordem INTEGER,

                data_criacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    area_tecnica_id
                )
                REFERENCES areas_tecnicas(
                    id
                ),

                UNIQUE (
                    area_tecnica_id,
                    nome
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
                        ativa IN (
                            0,
                            1
                        )
                    ),

                peso REAL NOT NULL
                    DEFAULT 1.0
                    CHECK (
                        peso >= 0
                    ),

                usa_star INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (
                        usa_star IN (
                            0,
                            1
                        )
                    ),

                data_criacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                area_tecnica_id INTEGER,

                subarea_tecnica_id INTEGER,

                FOREIGN KEY (
                    tipo_entrevista_id
                )
                REFERENCES tipos_entrevista(
                    id
                ),

                FOREIGN KEY (
                    competencia_id
                )
                REFERENCES competencias(
                    id
                ),

                FOREIGN KEY (
                    area_tecnica_id
                )
                REFERENCES areas_tecnicas(
                    id
                ),

                FOREIGN KEY (
                    subarea_tecnica_id
                )
                REFERENCES subareas_tecnicas(
                    id
                )

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

                area_tecnica_id INTEGER,

                subarea_tecnica_id INTEGER,

                area_tecnica_nome_aplicado TEXT,

                subarea_tecnica_nome_aplicado TEXT,

                FOREIGN KEY (
                    usuario_id
                )
                REFERENCES usuarios(
                    id
                ),

                FOREIGN KEY (
                    tipo_entrevista_id
                )
                REFERENCES tipos_entrevista(
                    id
                ),

                FOREIGN KEY (
                    area_tecnica_id
                )
                REFERENCES areas_tecnicas(
                    id
                ),

                FOREIGN KEY (
                    subarea_tecnica_id
                )
                REFERENCES subareas_tecnicas(
                    id
                )

            );
            """
        )


        # ====================================================
        # PERGUNTAS APLICADAS À ENTREVISTA
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entrevista_perguntas (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                entrevista_id INTEGER NOT NULL,

                pergunta_id INTEGER NOT NULL,

                pergunta_texto_aplicado TEXT NOT NULL,

                exemplo_esperado_aplicado TEXT,

                competencia_id_aplicada INTEGER NOT NULL,

                competencia_nome_aplicada TEXT NOT NULL,

                area_tecnica_id_aplicada INTEGER,

                area_tecnica_nome_aplicada TEXT,

                subarea_tecnica_id_aplicada INTEGER,

                subarea_tecnica_nome_aplicada TEXT,

                peso_pergunta_aplicado REAL NOT NULL
                    CHECK (
                        peso_pergunta_aplicado >= 0
                    ),

                usa_star_aplicado INTEGER NOT NULL
                    CHECK (
                        usa_star_aplicado IN (
                            0,
                            1
                        )
                    ),

                ordem_pergunta_aplicada INTEGER,

                data_aplicacao DATETIME
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    entrevista_id
                )
                REFERENCES entrevistas(
                    id
                )
                ON DELETE CASCADE,

                FOREIGN KEY (
                    pergunta_id
                )
                REFERENCES perguntas(
                    id
                ),

                UNIQUE (
                    entrevista_id,
                    pergunta_id
                )

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

                peso_pergunta_aplicado REAL,

                usa_star_aplicado INTEGER,

                ordem_pergunta_aplicada INTEGER,

                FOREIGN KEY (
                    entrevista_id
                )
                REFERENCES entrevistas(
                    id
                )
                ON DELETE CASCADE,

                FOREIGN KEY (
                    pergunta_id
                )
                REFERENCES perguntas(
                    id
                ),

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
                REFERENCES respostas(
                    id
                )
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

                peso_aplicado REAL,

                criterio_nome_aplicado TEXT,

                criterio_descricao_aplicada TEXT,

                criterio_ordem_aplicada INTEGER,

                FOREIGN KEY (
                    avaliacao_id
                )
                REFERENCES avaliacoes(
                    id
                )
                ON DELETE CASCADE,

                FOREIGN KEY (
                    criterio_id
                )
                REFERENCES criterios_avaliacao(
                    id
                ),

                UNIQUE (
                    avaliacao_id,
                    criterio_id
                )

            );
            """
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
                REFERENCES usuarios(
                    id
                )

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
        # EVOLUÇÃO DE BANCOS EXISTENTES
        # ====================================================

        _adicionar_coluna_se_ausente(
            cursor,
            "tipos_entrevista",
            "usa_area_tecnica",
            """
            INTEGER NOT NULL
            DEFAULT 0
            CHECK (
                usa_area_tecnica IN (
                    0,
                    1
                )
            )
            """
        )


        # ----------------------------------------------------
        # PERGUNTAS
        # ----------------------------------------------------

        _adicionar_coluna_se_ausente(
            cursor,
            "perguntas",
            "area_tecnica_id",
            """
            INTEGER
            REFERENCES areas_tecnicas(
                id
            )
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "perguntas",
            "subarea_tecnica_id",
            """
            INTEGER
            REFERENCES subareas_tecnicas(
                id
            )
            """
        )


        # ----------------------------------------------------
        # ENTREVISTAS
        # ----------------------------------------------------

        _adicionar_coluna_se_ausente(
            cursor,
            "entrevistas",
            "tipo_entrevista_nome_aplicado",
            """
            TEXT
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "entrevistas",
            "tipo_entrevista_descricao_aplicada",
            """
            TEXT
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "entrevistas",
            "area_tecnica_id",
            """
            INTEGER
            REFERENCES areas_tecnicas(
                id
            )
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "entrevistas",
            "subarea_tecnica_id",
            """
            INTEGER
            REFERENCES subareas_tecnicas(
                id
            )
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "entrevistas",
            "area_tecnica_nome_aplicado",
            """
            TEXT
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "entrevistas",
            "subarea_tecnica_nome_aplicado",
            """
            TEXT
            """
        )


        # ----------------------------------------------------
        # RESPOSTAS
        # ----------------------------------------------------

        _adicionar_coluna_se_ausente(
            cursor,
            "respostas",
            "pergunta_texto_aplicado",
            """
            TEXT
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "respostas",
            "exemplo_esperado_aplicado",
            """
            TEXT
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "respostas",
            "competencia_id_aplicada",
            """
            INTEGER
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "respostas",
            "competencia_nome_aplicada",
            """
            TEXT
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "respostas",
            "peso_pergunta_aplicado",
            """
            REAL
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "respostas",
            "usa_star_aplicado",
            """
            INTEGER
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "respostas",
            "ordem_pergunta_aplicada",
            """
            INTEGER
            """
        )


        # ----------------------------------------------------
        # AVALIAÇÃO POR CRITÉRIO
        # ----------------------------------------------------

        _adicionar_coluna_se_ausente(
            cursor,
            "avaliacao_criterios",
            "peso_aplicado",
            """
            REAL
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "avaliacao_criterios",
            "criterio_nome_aplicado",
            """
            TEXT
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "avaliacao_criterios",
            "criterio_descricao_aplicada",
            """
            TEXT
            """
        )

        _adicionar_coluna_se_ausente(
            cursor,
            "avaliacao_criterios",
            "criterio_ordem_aplicada",
            """
            INTEGER
            """
        )


        # ====================================================
        # MIGRAÇÃO DE TRIGGERS HISTÓRICOS
        # ====================================================
        #
        # Bancos criados em fases anteriores podem possuir
        # triggers antigos com nomes diferentes ou definições
        # anteriores às regras atuais de snapshot.
        #
        # CREATE TRIGGER IF NOT EXISTS não substitui um trigger
        # já existente. Por isso, antes dos backfills e da
        # recriação dos triggers oficiais desta versão, removemos:
        #
        # - triggers legados;
        # - triggers atuais que possam existir com definição antiga.
        #
        # Todos eles serão recriados mais abaixo com a definição
        # oficial desta versão.
        # ====================================================

        triggers_snapshot_para_recriar = (

            # ------------------------------------------------
            # Tipos de entrevista / área técnica
            # ------------------------------------------------

            "trg_tipos_entrevista_tecnica_area",

            # ------------------------------------------------
            # Proteção da subárea Geral
            # ------------------------------------------------

            "trg_subarea_geral_nao_inativar",
            "trg_subarea_geral_identidade_imutavel",
            "trg_subarea_geral_nao_excluir",

            # ------------------------------------------------
            # Snapshot da entrevista - nomes atuais
            # ------------------------------------------------

            "trg_entrevistas_snapshot_tipo_insert",
            "trg_entrevistas_snapshot_tipo_imutavel",
            "trg_entrevistas_snapshot_area_insert",
            "trg_entrevistas_area_imutavel",

            # ------------------------------------------------
            # Snapshot da entrevista - nomes legados
            # ------------------------------------------------

            "trg_entrevistas_tipo_snapshot_insert",
            "trg_entrevistas_tipo_snapshot_imutavel",

            # ------------------------------------------------
            # Snapshot da resposta
            # ------------------------------------------------

            "trg_respostas_snapshot_insert",
            "trg_respostas_snapshot_imutavel",

            # Trigger legado que impedia inserir snapshots
            # diretamente a partir de entrevista_perguntas.
            "trg_respostas_snapshot_insert_protegido",

            # ------------------------------------------------
            # Snapshot dos critérios
            # ------------------------------------------------

            "trg_avaliacao_criterios_snapshot_insert",
            "trg_avaliacao_criterios_snapshot_imutavel",

            # ------------------------------------------------
            # Perguntas congeladas da entrevista
            # ------------------------------------------------

            "trg_entrevista_perguntas_snapshot_imutavel"

        )


        for nome_trigger in triggers_snapshot_para_recriar:

            cursor.execute(
                f"DROP TRIGGER IF EXISTS {nome_trigger};"
            )


        # ====================================================
        # BACKFILL - TIPO DE ENTREVISTA
        # ====================================================

        cursor.execute(
            """
            UPDATE entrevistas

            SET tipo_entrevista_nome_aplicado = (

                SELECT
                    t.nome

                FROM tipos_entrevista t

                WHERE t.id =
                    entrevistas.tipo_entrevista_id

            )

            WHERE tipo_entrevista_nome_aplicado
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE entrevistas

            SET tipo_entrevista_descricao_aplicada = (

                SELECT
                    t.descricao

                FROM tipos_entrevista t

                WHERE t.id =
                    entrevistas.tipo_entrevista_id

            )

            WHERE tipo_entrevista_descricao_aplicada
                IS NULL;
            """
        )


        # ====================================================
        # BACKFILL - SNAPSHOT DAS RESPOSTAS
        # ====================================================

        cursor.execute(
            """
            UPDATE respostas

            SET pergunta_texto_aplicado = (

                SELECT
                    p.texto

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id

            )

            WHERE pergunta_texto_aplicado
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE respostas

            SET exemplo_esperado_aplicado = (

                SELECT
                    p.exemplo_esperado

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id

            )

            WHERE exemplo_esperado_aplicado
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE respostas

            SET competencia_id_aplicada = (

                SELECT
                    p.competencia_id

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id

            )

            WHERE competencia_id_aplicada
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE respostas

            SET competencia_nome_aplicada = (

                SELECT
                    c.nome

                FROM perguntas p

                INNER JOIN competencias c
                    ON c.id =
                        p.competencia_id

                WHERE p.id =
                    respostas.pergunta_id

            )

            WHERE competencia_nome_aplicada
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE respostas

            SET peso_pergunta_aplicado = (

                SELECT
                    p.peso

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id

            )

            WHERE peso_pergunta_aplicado
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE respostas

            SET usa_star_aplicado = (

                SELECT
                    p.usa_star

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id

            )

            WHERE usa_star_aplicado
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE respostas

            SET ordem_pergunta_aplicada = (

                SELECT
                    p.ordem

                FROM perguntas p

                WHERE p.id =
                    respostas.pergunta_id

            )

            WHERE ordem_pergunta_aplicada
                IS NULL;
            """
        )


        # ====================================================
        # BACKFILL - SNAPSHOT DOS CRITÉRIOS
        # ====================================================

        cursor.execute(
            """
            UPDATE avaliacao_criterios

            SET peso_aplicado = (

                SELECT
                    c.peso

                FROM criterios_avaliacao c

                WHERE c.id =
                    avaliacao_criterios.criterio_id

            )

            WHERE peso_aplicado
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE avaliacao_criterios

            SET criterio_nome_aplicado = (

                SELECT
                    c.nome

                FROM criterios_avaliacao c

                WHERE c.id =
                    avaliacao_criterios.criterio_id

            )

            WHERE criterio_nome_aplicado
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE avaliacao_criterios

            SET criterio_descricao_aplicada = (

                SELECT
                    c.descricao

                FROM criterios_avaliacao c

                WHERE c.id =
                    avaliacao_criterios.criterio_id

            )

            WHERE criterio_descricao_aplicada
                IS NULL;
            """
        )


        cursor.execute(
            """
            UPDATE avaliacao_criterios

            SET criterio_ordem_aplicada = (

                SELECT
                    c.ordem

                FROM criterios_avaliacao c

                WHERE c.id =
                    avaliacao_criterios.criterio_id

            )

            WHERE criterio_ordem_aplicada
                IS NULL;
            """
        )


        # ====================================================
        # CADASTRAR ÁREAS TÉCNICAS INICIAIS
        # ====================================================

        for (
            nome,
            descricao,
            ordem
        ) in AREAS_TECNICAS_INICIAIS:

            cursor.execute(
                """
                INSERT OR IGNORE INTO areas_tecnicas (

                    nome,
                    descricao,
                    ativo,
                    ordem

                )

                VALUES (
                    ?,
                    ?,
                    1,
                    ?
                )
                """,
                (
                    nome,
                    descricao,
                    ordem
                )
            )


            # ------------------------------------------------
            # RECUPERAR A ÁREA
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id

                FROM areas_tecnicas

                WHERE nome = ?
                    COLLATE NOCASE

                LIMIT 1
                """,
                (
                    nome,
                )
            )


            area = cursor.fetchone()


            if area is None:

                raise sqlite3.DatabaseError(
                    "Não foi possível localizar "
                    f"a área técnica '{nome}'."
                )


            # ------------------------------------------------
            # GARANTIR SUBÁREA GERAL
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT
                    id

                FROM subareas_tecnicas

                WHERE area_tecnica_id = ?
                  AND eh_geral = 1

                LIMIT 1
                """,
                (
                    area["id"],
                )
            )


            geral = cursor.fetchone()


            if geral is None:

                cursor.execute(
                    """
                    INSERT INTO subareas_tecnicas (

                        area_tecnica_id,
                        nome,
                        descricao,
                        eh_geral,
                        ativo,
                        ordem

                    )

                    VALUES (
                        ?,
                        'Geral',
                        ?,
                        1,
                        1,
                        1
                    )
                    """,
                    (
                        area["id"],

                        (
                            "Subárea padrão destinada "
                            "a perguntas gerais da área."
                        )
                    )
                )


        # ====================================================
        # CONFIGURAR TIPO TÉCNICA EXISTENTE
        # ====================================================

        cursor.execute(
            """
            UPDATE tipos_entrevista

            SET usa_area_tecnica = 1

            WHERE LOWER(nome) IN (
                'técnica',
                'tecnica'
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
                idx_perguntas_area_tecnica

            ON perguntas (
                area_tecnica_id
            );
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_perguntas_subarea_tecnica

            ON perguntas (
                subarea_tecnica_id
            );
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_subareas_tecnicas_area

            ON subareas_tecnicas (
                area_tecnica_id
            );
            """
        )


        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_subareas_tecnicas_uma_geral_por_area

            ON subareas_tecnicas (
                area_tecnica_id
            )

            WHERE eh_geral = 1;
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
                idx_entrevistas_area_tecnica

            ON entrevistas (
                area_tecnica_id
            );
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_entrevistas_subarea_tecnica

            ON entrevistas (
                subarea_tecnica_id
            );
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_entrevista_perguntas_entrevista

            ON entrevista_perguntas (
                entrevista_id
            );
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_entrevista_perguntas_pergunta

            ON entrevista_perguntas (
                pergunta_id
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
        # TRIGGER - NOVO TIPO TÉCNICA
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_tipos_entrevista_tecnica_area

            AFTER INSERT
            ON tipos_entrevista

            WHEN LOWER(NEW.nome) IN (
                'técnica',
                'tecnica'
            )

            BEGIN

                UPDATE tipos_entrevista

                SET usa_area_tecnica = 1

                WHERE id = NEW.id;

            END;
            """
        )


        # ====================================================
        # TRIGGER - GERAL NÃO PODE SER INATIVADA
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_subarea_geral_nao_inativar

            BEFORE UPDATE OF ativo
            ON subareas_tecnicas

            WHEN

                OLD.eh_geral = 1

                AND

                NEW.ativo = 0

            BEGIN

                SELECT RAISE(
                    ABORT,
                    'A subárea Geral não pode ser inativada.'
                );

            END;
            """
        )


        # ====================================================
        # TRIGGER - GERAL NÃO PODE SER RENOMEADA
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_subarea_geral_identidade_imutavel

            BEFORE UPDATE OF
                nome,
                eh_geral

            ON subareas_tecnicas

            WHEN

                OLD.eh_geral = 1

                AND

                (
                    NEW.eh_geral <> 1

                    OR

                    NEW.nome <> OLD.nome
                )

            BEGIN

                SELECT RAISE(
                    ABORT,
                    'A subárea Geral não pode ser renomeada ou descaracterizada.'
                );

            END;
            """
        )


        # ====================================================
        # TRIGGER - GERAL NÃO PODE SER EXCLUÍDA
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_subarea_geral_nao_excluir

            BEFORE DELETE
            ON subareas_tecnicas

            WHEN OLD.eh_geral = 1

            BEGIN

                SELECT RAISE(
                    ABORT,
                    'A subárea Geral não pode ser excluída.'
                );

            END;
            """
        )


        # ====================================================
        # TRIGGER - SNAPSHOT DO TIPO DE ENTREVISTA
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_entrevistas_snapshot_tipo_insert

            AFTER INSERT
            ON entrevistas

            WHEN
                NEW.tipo_entrevista_nome_aplicado
                IS NULL

            BEGIN

                UPDATE entrevistas

                SET

                    tipo_entrevista_nome_aplicado = (

                        SELECT
                            t.nome

                        FROM tipos_entrevista t

                        WHERE t.id =
                            NEW.tipo_entrevista_id

                    ),

                    tipo_entrevista_descricao_aplicada = (

                        SELECT
                            t.descricao

                        FROM tipos_entrevista t

                        WHERE t.id =
                            NEW.tipo_entrevista_id

                    )

                WHERE id =
                    NEW.id;

            END;
            """
        )


        # ====================================================
        # TRIGGER - TIPO HISTÓRICO É IMUTÁVEL
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_entrevistas_snapshot_tipo_imutavel

            BEFORE UPDATE OF

                tipo_entrevista_nome_aplicado,
                tipo_entrevista_descricao_aplicada

            ON entrevistas

            WHEN
                OLD.tipo_entrevista_nome_aplicado
                IS NOT NULL

            BEGIN

                SELECT RAISE(
                    ABORT,
                    'O snapshot do tipo de entrevista é imutável.'
                );

            END;
            """
        )


        # ====================================================
        # TRIGGER - SNAPSHOT DE ÁREA/SUBÁREA
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_entrevistas_snapshot_area_insert

            AFTER INSERT
            ON entrevistas

            WHEN

                NEW.area_tecnica_id
                    IS NOT NULL

                OR

                NEW.subarea_tecnica_id
                    IS NOT NULL

            BEGIN

                UPDATE entrevistas

                SET

                    area_tecnica_nome_aplicado = CASE

                        WHEN NEW.area_tecnica_id
                            IS NULL

                        THEN NULL

                        ELSE (

                            SELECT
                                a.nome

                            FROM areas_tecnicas a

                            WHERE a.id =
                                NEW.area_tecnica_id

                        )

                    END,

                    subarea_tecnica_nome_aplicado = CASE

                        WHEN NEW.subarea_tecnica_id
                            IS NULL

                        THEN NULL

                        ELSE (

                            SELECT
                                s.nome

                            FROM subareas_tecnicas s

                            WHERE s.id =
                                NEW.subarea_tecnica_id

                        )

                    END

                WHERE id =
                    NEW.id;

            END;
            """
        )


        # ====================================================
        # TRIGGER - ÁREA/SUBÁREA HISTÓRICAS SÃO IMUTÁVEIS
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_entrevistas_area_imutavel

            BEFORE UPDATE OF

                area_tecnica_id,
                subarea_tecnica_id,
                area_tecnica_nome_aplicado,
                subarea_tecnica_nome_aplicado

            ON entrevistas

            WHEN

                OLD.area_tecnica_nome_aplicado
                    IS NOT NULL

                OR

                OLD.subarea_tecnica_nome_aplicado
                    IS NOT NULL

            BEGIN

                SELECT RAISE(
                    ABORT,
                    'A área e a subárea aplicadas à entrevista são imutáveis.'
                );

            END;
            """
        )


        # ====================================================
        # TRIGGER - SNAPSHOT DA RESPOSTA
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_respostas_snapshot_insert

            AFTER INSERT
            ON respostas

            WHEN

                NEW.pergunta_texto_aplicado
                    IS NULL

                OR

                NEW.competencia_nome_aplicada
                    IS NULL

                OR

                NEW.peso_pergunta_aplicado
                    IS NULL

                OR

                NEW.usa_star_aplicado
                    IS NULL

            BEGIN

                UPDATE respostas

                SET

                    pergunta_texto_aplicado = COALESCE(

                        NEW.pergunta_texto_aplicado,

                        (
                            SELECT
                                p.texto

                            FROM perguntas p

                            WHERE p.id =
                                NEW.pergunta_id
                        )

                    ),

                    exemplo_esperado_aplicado = COALESCE(

                        NEW.exemplo_esperado_aplicado,

                        (
                            SELECT
                                p.exemplo_esperado

                            FROM perguntas p

                            WHERE p.id =
                                NEW.pergunta_id
                        )

                    ),

                    competencia_id_aplicada = COALESCE(

                        NEW.competencia_id_aplicada,

                        (
                            SELECT
                                p.competencia_id

                            FROM perguntas p

                            WHERE p.id =
                                NEW.pergunta_id
                        )

                    ),

                    competencia_nome_aplicada = COALESCE(

                        NEW.competencia_nome_aplicada,

                        (
                            SELECT
                                c.nome

                            FROM perguntas p

                            INNER JOIN competencias c

                                ON c.id =
                                    p.competencia_id

                            WHERE p.id =
                                NEW.pergunta_id
                        )

                    ),

                    peso_pergunta_aplicado = COALESCE(

                        NEW.peso_pergunta_aplicado,

                        (
                            SELECT
                                p.peso

                            FROM perguntas p

                            WHERE p.id =
                                NEW.pergunta_id
                        )

                    ),

                    usa_star_aplicado = COALESCE(

                        NEW.usa_star_aplicado,

                        (
                            SELECT
                                p.usa_star

                            FROM perguntas p

                            WHERE p.id =
                                NEW.pergunta_id
                        )

                    ),

                    ordem_pergunta_aplicada = COALESCE(

                        NEW.ordem_pergunta_aplicada,

                        (
                            SELECT
                                p.ordem

                            FROM perguntas p

                            WHERE p.id =
                                NEW.pergunta_id
                        )

                    )

                WHERE id =
                    NEW.id;

            END;
            """
        )


        # ====================================================
        # TRIGGER - SNAPSHOT DA RESPOSTA É IMUTÁVEL
        # ====================================================

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

            WHEN

                OLD.pergunta_texto_aplicado
                    IS NOT NULL

                AND

                OLD.competencia_nome_aplicada
                    IS NOT NULL

                AND

                OLD.peso_pergunta_aplicado
                    IS NOT NULL

                AND

                OLD.usa_star_aplicado
                    IS NOT NULL

            BEGIN

                SELECT RAISE(
                    ABORT,
                    'O snapshot histórico da pergunta é imutável.'
                );

            END;
            """
        )


        # ====================================================
        # TRIGGER - SNAPSHOT DOS CRITÉRIOS
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_avaliacao_criterios_snapshot_insert

            AFTER INSERT
            ON avaliacao_criterios

            WHEN

                NEW.peso_aplicado
                    IS NULL

                OR

                NEW.criterio_nome_aplicado
                    IS NULL

            BEGIN

                UPDATE avaliacao_criterios

                SET

                    peso_aplicado = COALESCE(

                        NEW.peso_aplicado,

                        (
                            SELECT
                                c.peso

                            FROM criterios_avaliacao c

                            WHERE c.id =
                                NEW.criterio_id
                        )

                    ),

                    criterio_nome_aplicado = COALESCE(

                        NEW.criterio_nome_aplicado,

                        (
                            SELECT
                                c.nome

                            FROM criterios_avaliacao c

                            WHERE c.id =
                                NEW.criterio_id
                        )

                    ),

                    criterio_descricao_aplicada = COALESCE(

                        NEW.criterio_descricao_aplicada,

                        (
                            SELECT
                                c.descricao

                            FROM criterios_avaliacao c

                            WHERE c.id =
                                NEW.criterio_id
                        )

                    ),

                    criterio_ordem_aplicada = COALESCE(

                        NEW.criterio_ordem_aplicada,

                        (
                            SELECT
                                c.ordem

                            FROM criterios_avaliacao c

                            WHERE c.id =
                                NEW.criterio_id
                        )

                    )

                WHERE id =
                    NEW.id;

            END;
            """
        )


        # ====================================================
        # TRIGGER - SNAPSHOT DO CRITÉRIO É IMUTÁVEL
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_avaliacao_criterios_snapshot_imutavel

            BEFORE UPDATE OF

                peso_aplicado,
                criterio_nome_aplicado,
                criterio_descricao_aplicada,
                criterio_ordem_aplicada

            ON avaliacao_criterios

            WHEN

                OLD.peso_aplicado
                    IS NOT NULL

                AND

                OLD.criterio_nome_aplicado
                    IS NOT NULL

            BEGIN

                SELECT RAISE(
                    ABORT,
                    'O snapshot histórico do critério é imutável.'
                );

            END;
            """
        )


        # ====================================================
        # TRIGGER - ENTREVISTA_PERGUNTAS É IMUTÁVEL
        # ====================================================

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS
                trg_entrevista_perguntas_snapshot_imutavel

            BEFORE UPDATE
            ON entrevista_perguntas

            BEGIN

                SELECT RAISE(
                    ABORT,
                    'O snapshot da pergunta aplicada à entrevista é imutável.'
                );

            END;
            """
        )


        # ====================================================
        # CONFIRMAR ALTERAÇÕES
        # ====================================================

        conexao.commit()


        print(
            "Banco de dados versão 0.6 "
            "criado/atualizado com sucesso."
        )


    except sqlite3.Error as erro:

        conexao.rollback()


        print(
            "Erro ao criar/atualizar "
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