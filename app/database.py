"""Conexão e criação das tabelas do Simulador de Entrevistas."""

import os
import sqlite3

# Pasta e arquivo usados pelo SQLite.
PASTA_BANCO = "data"
NOME_BANCO = "entrevistas.db"
CAMINHO_BANCO = os.path.join(PASTA_BANCO, NOME_BANCO)

# Áreas criadas automaticamente quando o banco é preparado pela primeira vez.
AREAS_TECNICAS_INICIAIS = (
    ("Direito", "Área destinada a entrevistas técnicas relacionadas ao campo jurídico.", 1),
    ("Psicologia", "Área destinada a entrevistas técnicas relacionadas à Psicologia.", 2),
    ("Administração", "Área destinada a entrevistas técnicas relacionadas à Administração.", 3),
    ("Economia", "Área destinada a entrevistas técnicas relacionadas à Economia.", 4),
    ("Ciências Contábeis", "Área destinada a entrevistas técnicas relacionadas às Ciências Contábeis.", 5),
    ("Tecnologia", "Área destinada a entrevistas técnicas relacionadas à Tecnologia e áreas correlatas.", 6)
)


def conectar_banco():
    """Abre a conexão com o SQLite e ativa as chaves estrangeiras."""
    # Garante que a pasta do banco exista antes de abrir o arquivo.
    os.makedirs(PASTA_BANCO, exist_ok=True)

    # row_factory permite acessar as colunas pelo nome, como registro["id"].
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON;")
    return conexao


def _colunas_tabela(cursor, tabela):
    """Retorna um conjunto com os nomes das colunas existentes em uma tabela."""
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas = set()

    # Percorre o resultado e guarda apenas o nome de cada coluna.
    for registro in cursor.fetchall():
        colunas.add(registro["name"])

    return colunas


def _adicionar_coluna_se_ausente(cursor, tabela, coluna, definicao):
    """Adiciona uma coluna apenas quando ela ainda não existe no banco."""
    # Essa verificação permite atualizar bancos antigos sem apagar os dados.
    if coluna in _colunas_tabela(cursor, tabela):
        return

    cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def criar_tabelas():
    """Cria as tabelas, atualiza bancos antigos e prepara índices e triggers."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # ====================================================
        # TABELAS PRINCIPAIS
        # ====================================================

        # Guarda os usuários que acessam o sistema.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                perfil TEXT NOT NULL DEFAULT 'estudante' CHECK (perfil IN ('estudante', 'administrador')),
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                ultimo_acesso DATETIME
            );
            """
        )

        # Define os tipos de entrevista, como Técnica ou Comportamental.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tipos_entrevista (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                usa_area_tecnica INTEGER NOT NULL DEFAULT 0 CHECK (usa_area_tecnica IN (0, 1))
            );
            """
        )

        # Guarda as competências avaliadas pelas perguntas.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS competencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                ativa INTEGER NOT NULL DEFAULT 1 CHECK (ativa IN (0, 1))
            );
            """
        )

        # Guarda os critérios usados para calcular a avaliação das respostas.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS criterios_avaliacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                peso REAL NOT NULL DEFAULT 1.0 CHECK (peso >= 0),
                ordem INTEGER,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
            );
            """
        )

        # Guarda as áreas disponíveis para entrevistas técnicas.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS areas_tecnicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL COLLATE NOCASE UNIQUE,
                descricao TEXT,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                ordem INTEGER,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Cada subárea pertence a uma área e uma delas pode ser a subárea Geral.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subareas_tecnicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area_tecnica_id INTEGER NOT NULL,
                nome TEXT NOT NULL COLLATE NOCASE,
                descricao TEXT,
                eh_geral INTEGER NOT NULL DEFAULT 0 CHECK (eh_geral IN (0, 1)),
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                ordem INTEGER,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (area_tecnica_id) REFERENCES areas_tecnicas(id),
                UNIQUE (area_tecnica_id, nome)
            );
            """
        )

        # Guarda todas as perguntas cadastradas no catálogo do sistema.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS perguntas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_entrevista_id INTEGER NOT NULL,
                competencia_id INTEGER NOT NULL,
                texto TEXT NOT NULL,
                exemplo_esperado TEXT,
                ordem INTEGER,
                ativa INTEGER NOT NULL DEFAULT 1 CHECK (ativa IN (0, 1)),
                peso REAL NOT NULL DEFAULT 1.0 CHECK (peso >= 0),
                usa_star INTEGER NOT NULL DEFAULT 0 CHECK (usa_star IN (0, 1)),
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                area_tecnica_id INTEGER,
                subarea_tecnica_id INTEGER,
                FOREIGN KEY (tipo_entrevista_id) REFERENCES tipos_entrevista(id),
                FOREIGN KEY (competencia_id) REFERENCES competencias(id),
                FOREIGN KEY (area_tecnica_id) REFERENCES areas_tecnicas(id),
                FOREIGN KEY (subarea_tecnica_id) REFERENCES subareas_tecnicas(id)
            );
            """
        )

        # Guarda cada entrevista iniciada por um estudante.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entrevistas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                tipo_entrevista_id INTEGER NOT NULL,
                data_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_fim DATETIME,
                status TEXT NOT NULL DEFAULT 'em_andamento' CHECK (
                    status IN ('em_andamento', 'finalizada', 'em_analise', 'avaliada', 'erro_analise', 'cancelada')
                ),
                pontuacao_final REAL,
                observacoes TEXT,
                tipo_entrevista_nome_aplicado TEXT,
                tipo_entrevista_descricao_aplicada TEXT,
                area_tecnica_id INTEGER,
                subarea_tecnica_id INTEGER,
                area_tecnica_nome_aplicado TEXT,
                subarea_tecnica_nome_aplicado TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (tipo_entrevista_id) REFERENCES tipos_entrevista(id),
                FOREIGN KEY (area_tecnica_id) REFERENCES areas_tecnicas(id),
                FOREIGN KEY (subarea_tecnica_id) REFERENCES subareas_tecnicas(id)
            );
            """
        )

        # Congela as perguntas escolhidas quando a entrevista é iniciada.
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
                peso_pergunta_aplicado REAL NOT NULL CHECK (peso_pergunta_aplicado >= 0),
                usa_star_aplicado INTEGER NOT NULL CHECK (usa_star_aplicado IN (0, 1)),
                ordem_pergunta_aplicada INTEGER,
                data_aplicacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entrevista_id) REFERENCES entrevistas(id) ON DELETE CASCADE,
                FOREIGN KEY (pergunta_id) REFERENCES perguntas(id),
                UNIQUE (entrevista_id, pergunta_id)
            );
            """
        )

        # Guarda as respostas e uma cópia dos dados históricos da pergunta.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS respostas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entrevista_id INTEGER NOT NULL,
                pergunta_id INTEGER NOT NULL,
                texto_resposta TEXT NOT NULL,
                tempo_resposta INTEGER CHECK (tempo_resposta IS NULL OR tempo_resposta >= 0),
                data_resposta DATETIME DEFAULT CURRENT_TIMESTAMP,
                pergunta_texto_aplicado TEXT,
                exemplo_esperado_aplicado TEXT,
                competencia_id_aplicada INTEGER,
                competencia_nome_aplicada TEXT,
                peso_pergunta_aplicado REAL,
                usa_star_aplicado INTEGER,
                ordem_pergunta_aplicada INTEGER,
                FOREIGN KEY (entrevista_id) REFERENCES entrevistas(id) ON DELETE CASCADE,
                FOREIGN KEY (pergunta_id) REFERENCES perguntas(id),
                UNIQUE (entrevista_id, pergunta_id)
            );
            """
        )

        # Guarda a avaliação geral feita para cada resposta.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS avaliacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resposta_id INTEGER NOT NULL UNIQUE,
                pontuacao REAL CHECK (pontuacao IS NULL OR (pontuacao >= 0 AND pontuacao <= 10)),
                pontos_fortes TEXT,
                pontos_melhoria TEXT,
                feedback TEXT,
                modelo_ia TEXT,
                data_avaliacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resposta_id) REFERENCES respostas(id) ON DELETE CASCADE
            );
            """
        )

        # Guarda a nota recebida em cada critério da avaliação.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS avaliacao_criterios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                avaliacao_id INTEGER NOT NULL,
                criterio_id INTEGER NOT NULL,
                nota REAL NOT NULL CHECK (nota >= 0 AND nota <= 10),
                observacao TEXT,
                peso_aplicado REAL,
                criterio_nome_aplicado TEXT,
                criterio_descricao_aplicada TEXT,
                criterio_ordem_aplicada INTEGER,
                FOREIGN KEY (avaliacao_id) REFERENCES avaliacoes(id) ON DELETE CASCADE,
                FOREIGN KEY (criterio_id) REFERENCES criterios_avaliacao(id),
                UNIQUE (avaliacao_id, criterio_id)
            );
            """
        )

        # Registra ações realizadas pelos usuários.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS historico_acesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                acao TEXT NOT NULL,
                descricao TEXT,
                data_acao DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );
            """
        )

        # Guarda configurações gerais do sistema.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chave TEXT NOT NULL UNIQUE,
                valor TEXT,
                descricao TEXT,
                data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # ====================================================
        # ATUALIZAÇÃO DE BANCOS ANTIGOS
        # ====================================================

        # Adiciona campos que podem não existir em bancos criados em fases anteriores.
        _adicionar_coluna_se_ausente(
            cursor,
            "tipos_entrevista",
            "usa_area_tecnica",
            "INTEGER NOT NULL DEFAULT 0 CHECK (usa_area_tecnica IN (0, 1))"
        )

        _adicionar_coluna_se_ausente(cursor, "perguntas", "area_tecnica_id", "INTEGER REFERENCES areas_tecnicas(id)")
        _adicionar_coluna_se_ausente(cursor, "perguntas", "subarea_tecnica_id", "INTEGER REFERENCES subareas_tecnicas(id)")

        _adicionar_coluna_se_ausente(cursor, "entrevistas", "tipo_entrevista_nome_aplicado", "TEXT")
        _adicionar_coluna_se_ausente(cursor, "entrevistas", "tipo_entrevista_descricao_aplicada", "TEXT")
        _adicionar_coluna_se_ausente(cursor, "entrevistas", "area_tecnica_id", "INTEGER REFERENCES areas_tecnicas(id)")
        _adicionar_coluna_se_ausente(cursor, "entrevistas", "subarea_tecnica_id", "INTEGER REFERENCES subareas_tecnicas(id)")
        _adicionar_coluna_se_ausente(cursor, "entrevistas", "area_tecnica_nome_aplicado", "TEXT")
        _adicionar_coluna_se_ausente(cursor, "entrevistas", "subarea_tecnica_nome_aplicado", "TEXT")

        _adicionar_coluna_se_ausente(cursor, "respostas", "pergunta_texto_aplicado", "TEXT")
        _adicionar_coluna_se_ausente(cursor, "respostas", "exemplo_esperado_aplicado", "TEXT")
        _adicionar_coluna_se_ausente(cursor, "respostas", "competencia_id_aplicada", "INTEGER")
        _adicionar_coluna_se_ausente(cursor, "respostas", "competencia_nome_aplicada", "TEXT")
        _adicionar_coluna_se_ausente(cursor, "respostas", "peso_pergunta_aplicado", "REAL")
        _adicionar_coluna_se_ausente(cursor, "respostas", "usa_star_aplicado", "INTEGER")
        _adicionar_coluna_se_ausente(cursor, "respostas", "ordem_pergunta_aplicada", "INTEGER")

        _adicionar_coluna_se_ausente(cursor, "avaliacao_criterios", "peso_aplicado", "REAL")
        _adicionar_coluna_se_ausente(cursor, "avaliacao_criterios", "criterio_nome_aplicado", "TEXT")
        _adicionar_coluna_se_ausente(cursor, "avaliacao_criterios", "criterio_descricao_aplicada", "TEXT")
        _adicionar_coluna_se_ausente(cursor, "avaliacao_criterios", "criterio_ordem_aplicada", "INTEGER")

        # ====================================================
        # RECRIAÇÃO DOS TRIGGERS ATUAIS
        # ====================================================

        # Bancos antigos podem ter triggers com a mesma função, mas com regras antigas.
        # Por isso os triggers abaixo são removidos e criados novamente mais adiante.
        triggers_para_recriar = (
            "trg_tipos_entrevista_tecnica_area",
            "trg_subarea_geral_nao_inativar",
            "trg_subarea_geral_identidade_imutavel",
            "trg_subarea_geral_nao_excluir",
            "trg_entrevistas_snapshot_tipo_insert",
            "trg_entrevistas_snapshot_tipo_imutavel",
            "trg_entrevistas_snapshot_area_insert",
            "trg_entrevistas_area_imutavel",
            "trg_entrevistas_tipo_snapshot_insert",
            "trg_entrevistas_tipo_snapshot_imutavel",
            "trg_respostas_snapshot_insert",
            "trg_respostas_snapshot_imutavel",
            "trg_respostas_snapshot_insert_protegido",
            "trg_avaliacao_criterios_snapshot_insert",
            "trg_avaliacao_criterios_snapshot_imutavel",
            "trg_entrevista_perguntas_snapshot_imutavel"
        )

        for nome_trigger in triggers_para_recriar:
            cursor.execute(f"DROP TRIGGER IF EXISTS {nome_trigger};")

        # ====================================================
        # PREENCHIMENTO DE SNAPSHOTS ANTIGOS
        # ====================================================

        # Preenche o tipo histórico nas entrevistas antigas.
        cursor.execute(
            """
            UPDATE entrevistas
            SET tipo_entrevista_nome_aplicado = (
                SELECT t.nome FROM tipos_entrevista t WHERE t.id = entrevistas.tipo_entrevista_id
            )
            WHERE tipo_entrevista_nome_aplicado IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE entrevistas
            SET tipo_entrevista_descricao_aplicada = (
                SELECT t.descricao FROM tipos_entrevista t WHERE t.id = entrevistas.tipo_entrevista_id
            )
            WHERE tipo_entrevista_descricao_aplicada IS NULL;
            """
        )

        # Preenche nas respostas antigas os dados da pergunta usada na época.
        cursor.execute(
            """
            UPDATE respostas
            SET pergunta_texto_aplicado = (
                SELECT p.texto FROM perguntas p WHERE p.id = respostas.pergunta_id
            )
            WHERE pergunta_texto_aplicado IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE respostas
            SET exemplo_esperado_aplicado = (
                SELECT p.exemplo_esperado FROM perguntas p WHERE p.id = respostas.pergunta_id
            )
            WHERE exemplo_esperado_aplicado IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE respostas
            SET competencia_id_aplicada = (
                SELECT p.competencia_id FROM perguntas p WHERE p.id = respostas.pergunta_id
            )
            WHERE competencia_id_aplicada IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE respostas
            SET competencia_nome_aplicada = (
                SELECT c.nome
                FROM perguntas p
                INNER JOIN competencias c ON c.id = p.competencia_id
                WHERE p.id = respostas.pergunta_id
            )
            WHERE competencia_nome_aplicada IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE respostas
            SET peso_pergunta_aplicado = (
                SELECT p.peso FROM perguntas p WHERE p.id = respostas.pergunta_id
            )
            WHERE peso_pergunta_aplicado IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE respostas
            SET usa_star_aplicado = (
                SELECT p.usa_star FROM perguntas p WHERE p.id = respostas.pergunta_id
            )
            WHERE usa_star_aplicado IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE respostas
            SET ordem_pergunta_aplicada = (
                SELECT p.ordem FROM perguntas p WHERE p.id = respostas.pergunta_id
            )
            WHERE ordem_pergunta_aplicada IS NULL;
            """
        )

        # Preenche os dados históricos dos critérios em avaliações antigas.
        cursor.execute(
            """
            UPDATE avaliacao_criterios
            SET peso_aplicado = (
                SELECT c.peso FROM criterios_avaliacao c WHERE c.id = avaliacao_criterios.criterio_id
            )
            WHERE peso_aplicado IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE avaliacao_criterios
            SET criterio_nome_aplicado = (
                SELECT c.nome FROM criterios_avaliacao c WHERE c.id = avaliacao_criterios.criterio_id
            )
            WHERE criterio_nome_aplicado IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE avaliacao_criterios
            SET criterio_descricao_aplicada = (
                SELECT c.descricao FROM criterios_avaliacao c WHERE c.id = avaliacao_criterios.criterio_id
            )
            WHERE criterio_descricao_aplicada IS NULL;
            """
        )

        cursor.execute(
            """
            UPDATE avaliacao_criterios
            SET criterio_ordem_aplicada = (
                SELECT c.ordem FROM criterios_avaliacao c WHERE c.id = avaliacao_criterios.criterio_id
            )
            WHERE criterio_ordem_aplicada IS NULL;
            """
        )

        # ====================================================
        # ÁREAS E SUBÁREA GERAL
        # ====================================================

        # Garante as seis áreas iniciais e uma subárea Geral para cada uma.
        for nome, descricao, ordem in AREAS_TECNICAS_INICIAIS:
            cursor.execute(
                """
                INSERT OR IGNORE INTO areas_tecnicas (nome, descricao, ativo, ordem)
                VALUES (?, ?, 1, ?)
                """,
                (nome, descricao, ordem)
            )

            cursor.execute(
                "SELECT id FROM areas_tecnicas WHERE nome = ? COLLATE NOCASE LIMIT 1",
                (nome,)
            )

            area = cursor.fetchone()

            if area is None:
                raise sqlite3.DatabaseError(f"Não foi possível localizar a área técnica '{nome}'.")

            cursor.execute(
                """
                SELECT id FROM subareas_tecnicas
                WHERE area_tecnica_id = ? AND eh_geral = 1
                LIMIT 1
                """,
                (area["id"],)
            )

            geral = cursor.fetchone()

            if geral is None:
                cursor.execute(
                    """
                    INSERT INTO subareas_tecnicas (
                        area_tecnica_id, nome, descricao, eh_geral, ativo, ordem
                    )
                    VALUES (?, 'Geral', ?, 1, 1, 1)
                    """,
                    (area["id"], "Subárea padrão destinada a perguntas gerais da área.")
                )

        # Tipos chamados Técnica usam área técnica. A regra usa o nome e não um ID fixo.
        cursor.execute(
            """
            UPDATE tipos_entrevista
            SET usa_area_tecnica = 1
            WHERE LOWER(nome) IN ('técnica', 'tecnica');
            """
        )

        # ====================================================
        # ÍNDICES
        # ====================================================

        # Os índices abaixo aceleram as consultas mais usadas pelo sistema.
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_perguntas_tipo ON perguntas(tipo_entrevista_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_perguntas_competencia ON perguntas(competencia_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_perguntas_area_tecnica ON perguntas(area_tecnica_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_perguntas_subarea_tecnica ON perguntas(subarea_tecnica_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subareas_tecnicas_area ON subareas_tecnicas(area_tecnica_id);")

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_subareas_tecnicas_uma_geral_por_area
            ON subareas_tecnicas(area_tecnica_id)
            WHERE eh_geral = 1;
            """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entrevistas_usuario ON entrevistas(usuario_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entrevistas_area_tecnica ON entrevistas(area_tecnica_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entrevistas_subarea_tecnica ON entrevistas(subarea_tecnica_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entrevista_perguntas_entrevista ON entrevista_perguntas(entrevista_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entrevista_perguntas_pergunta ON entrevista_perguntas(pergunta_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_respostas_entrevista ON respostas(entrevista_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_avaliacao_criterios_avaliacao ON avaliacao_criterios(avaliacao_id);")

        # ====================================================
        # TRIGGERS DE PROTEÇÃO E SNAPSHOT
        # ====================================================

        # Se um novo tipo for chamado Técnica, ele passa a usar área técnica automaticamente.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_tipos_entrevista_tecnica_area
            AFTER INSERT ON tipos_entrevista
            WHEN LOWER(NEW.nome) IN ('técnica', 'tecnica')
            BEGIN
                UPDATE tipos_entrevista SET usa_area_tecnica = 1 WHERE id = NEW.id;
            END;
            """
        )

        # A subárea Geral é obrigatória e não pode ser inativada.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_subarea_geral_nao_inativar
            BEFORE UPDATE OF ativo ON subareas_tecnicas
            WHEN OLD.eh_geral = 1 AND NEW.ativo = 0
            BEGIN
                SELECT RAISE(ABORT, 'A subárea Geral não pode ser inativada.');
            END;
            """
        )

        # A subárea Geral não pode ser renomeada nem deixar de ser Geral.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_subarea_geral_identidade_imutavel
            BEFORE UPDATE OF nome, eh_geral ON subareas_tecnicas
            WHEN OLD.eh_geral = 1 AND (NEW.eh_geral <> 1 OR NEW.nome <> OLD.nome)
            BEGIN
                SELECT RAISE(ABORT, 'A subárea Geral não pode ser renomeada ou descaracterizada.');
            END;
            """
        )

        # Impede a exclusão da subárea Geral diretamente pelo banco.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_subarea_geral_nao_excluir
            BEFORE DELETE ON subareas_tecnicas
            WHEN OLD.eh_geral = 1
            BEGIN
                SELECT RAISE(ABORT, 'A subárea Geral não pode ser excluída.');
            END;
            """
        )

        # Copia o nome e a descrição do tipo quando uma entrevista é criada.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_entrevistas_snapshot_tipo_insert
            AFTER INSERT ON entrevistas
            WHEN NEW.tipo_entrevista_nome_aplicado IS NULL
            BEGIN
                UPDATE entrevistas
                SET tipo_entrevista_nome_aplicado = (
                        SELECT t.nome FROM tipos_entrevista t WHERE t.id = NEW.tipo_entrevista_id
                    ),
                    tipo_entrevista_descricao_aplicada = (
                        SELECT t.descricao FROM tipos_entrevista t WHERE t.id = NEW.tipo_entrevista_id
                    )
                WHERE id = NEW.id;
            END;
            """
        )

        # O tipo histórico de uma entrevista não pode mudar depois de registrado.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_entrevistas_snapshot_tipo_imutavel
            BEFORE UPDATE OF tipo_entrevista_nome_aplicado, tipo_entrevista_descricao_aplicada ON entrevistas
            WHEN OLD.tipo_entrevista_nome_aplicado IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'O snapshot do tipo de entrevista é imutável.');
            END;
            """
        )

        # Copia os nomes da área e da subárea usadas em uma entrevista técnica.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_entrevistas_snapshot_area_insert
            AFTER INSERT ON entrevistas
            WHEN NEW.area_tecnica_id IS NOT NULL OR NEW.subarea_tecnica_id IS NOT NULL
            BEGIN
                UPDATE entrevistas
                SET area_tecnica_nome_aplicado = CASE
                        WHEN NEW.area_tecnica_id IS NULL THEN NULL
                        ELSE (SELECT a.nome FROM areas_tecnicas a WHERE a.id = NEW.area_tecnica_id)
                    END,
                    subarea_tecnica_nome_aplicado = CASE
                        WHEN NEW.subarea_tecnica_id IS NULL THEN NULL
                        ELSE (SELECT s.nome FROM subareas_tecnicas s WHERE s.id = NEW.subarea_tecnica_id)
                    END
                WHERE id = NEW.id;
            END;
            """
        )

        # A área e a subárea históricas não podem ser alteradas depois do início da entrevista.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_entrevistas_area_imutavel
            BEFORE UPDATE OF area_tecnica_id, subarea_tecnica_id, area_tecnica_nome_aplicado, subarea_tecnica_nome_aplicado
            ON entrevistas
            WHEN OLD.area_tecnica_nome_aplicado IS NOT NULL OR OLD.subarea_tecnica_nome_aplicado IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'A área e a subárea aplicadas à entrevista são imutáveis.');
            END;
            """
        )

        # Completa o snapshot da pergunta quando uma resposta é inserida sem todos os campos históricos.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_respostas_snapshot_insert
            AFTER INSERT ON respostas
            WHEN NEW.pergunta_texto_aplicado IS NULL
              OR NEW.competencia_nome_aplicada IS NULL
              OR NEW.peso_pergunta_aplicado IS NULL
              OR NEW.usa_star_aplicado IS NULL
            BEGIN
                UPDATE respostas
                SET pergunta_texto_aplicado = COALESCE(
                        NEW.pergunta_texto_aplicado,
                        (SELECT p.texto FROM perguntas p WHERE p.id = NEW.pergunta_id)
                    ),
                    exemplo_esperado_aplicado = COALESCE(
                        NEW.exemplo_esperado_aplicado,
                        (SELECT p.exemplo_esperado FROM perguntas p WHERE p.id = NEW.pergunta_id)
                    ),
                    competencia_id_aplicada = COALESCE(
                        NEW.competencia_id_aplicada,
                        (SELECT p.competencia_id FROM perguntas p WHERE p.id = NEW.pergunta_id)
                    ),
                    competencia_nome_aplicada = COALESCE(
                        NEW.competencia_nome_aplicada,
                        (
                            SELECT c.nome
                            FROM perguntas p
                            INNER JOIN competencias c ON c.id = p.competencia_id
                            WHERE p.id = NEW.pergunta_id
                        )
                    ),
                    peso_pergunta_aplicado = COALESCE(
                        NEW.peso_pergunta_aplicado,
                        (SELECT p.peso FROM perguntas p WHERE p.id = NEW.pergunta_id)
                    ),
                    usa_star_aplicado = COALESCE(
                        NEW.usa_star_aplicado,
                        (SELECT p.usa_star FROM perguntas p WHERE p.id = NEW.pergunta_id)
                    ),
                    ordem_pergunta_aplicada = COALESCE(
                        NEW.ordem_pergunta_aplicada,
                        (SELECT p.ordem FROM perguntas p WHERE p.id = NEW.pergunta_id)
                    )
                WHERE id = NEW.id;
            END;
            """
        )

        # Impede a alteração dos dados históricos da pergunta depois da resposta registrada.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_respostas_snapshot_imutavel
            BEFORE UPDATE OF pergunta_texto_aplicado, exemplo_esperado_aplicado, competencia_id_aplicada,
                competencia_nome_aplicada, peso_pergunta_aplicado, usa_star_aplicado, ordem_pergunta_aplicada
            ON respostas
            WHEN OLD.pergunta_texto_aplicado IS NOT NULL
              AND OLD.competencia_nome_aplicada IS NOT NULL
              AND OLD.peso_pergunta_aplicado IS NOT NULL
              AND OLD.usa_star_aplicado IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'O snapshot histórico da pergunta é imutável.');
            END;
            """
        )

        # Completa o snapshot do critério quando uma nota é inserida.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_avaliacao_criterios_snapshot_insert
            AFTER INSERT ON avaliacao_criterios
            WHEN NEW.peso_aplicado IS NULL OR NEW.criterio_nome_aplicado IS NULL
            BEGIN
                UPDATE avaliacao_criterios
                SET peso_aplicado = COALESCE(
                        NEW.peso_aplicado,
                        (SELECT c.peso FROM criterios_avaliacao c WHERE c.id = NEW.criterio_id)
                    ),
                    criterio_nome_aplicado = COALESCE(
                        NEW.criterio_nome_aplicado,
                        (SELECT c.nome FROM criterios_avaliacao c WHERE c.id = NEW.criterio_id)
                    ),
                    criterio_descricao_aplicada = COALESCE(
                        NEW.criterio_descricao_aplicada,
                        (SELECT c.descricao FROM criterios_avaliacao c WHERE c.id = NEW.criterio_id)
                    ),
                    criterio_ordem_aplicada = COALESCE(
                        NEW.criterio_ordem_aplicada,
                        (SELECT c.ordem FROM criterios_avaliacao c WHERE c.id = NEW.criterio_id)
                    )
                WHERE id = NEW.id;
            END;
            """
        )

        # Impede a alteração do critério histórico depois que a avaliação foi registrada.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_avaliacao_criterios_snapshot_imutavel
            BEFORE UPDATE OF peso_aplicado, criterio_nome_aplicado, criterio_descricao_aplicada, criterio_ordem_aplicada
            ON avaliacao_criterios
            WHEN OLD.peso_aplicado IS NOT NULL AND OLD.criterio_nome_aplicado IS NOT NULL
            BEGIN
                SELECT RAISE(ABORT, 'O snapshot histórico do critério é imutável.');
            END;
            """
        )

        # As perguntas congeladas de uma entrevista não podem ser alteradas depois de criadas.
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_entrevista_perguntas_snapshot_imutavel
            BEFORE UPDATE ON entrevista_perguntas
            BEGIN
                SELECT RAISE(ABORT, 'O snapshot da pergunta aplicada à entrevista é imutável.');
            END;
            """
        )

        # Confirma todas as alterações feitas durante a preparação do banco.
        conexao.commit()
        print("Banco de dados criado/atualizado com sucesso.")

    except sqlite3.Error as erro:
        # Se qualquer comando SQL falhar, desfaz o que ainda não foi confirmado.
        conexao.rollback()
        print(f"Erro ao criar/atualizar o banco de dados: {erro}")
        raise

    finally:
        # A conexão sempre é fechada, mesmo quando ocorre um erro.
        conexao.close()


# Permite executar este arquivo diretamente para preparar o banco.
if __name__ == "__main__":
    criar_tabelas()