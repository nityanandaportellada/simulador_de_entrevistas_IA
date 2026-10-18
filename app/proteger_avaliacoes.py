
"""Migração adicional para proteger os estados e as avaliações no SQLite.

Execute após preparar o banco com python -m app.database.
As regras são idempotentes e permanecem após novas execuções de app.database.
"""

import sqlite3

from .database import conectar_banco

TRIGGERS = (
    "trg_entrevistas_estado_seguro",
    "trg_entrevistas_identidade_segura",
    "trg_entrevistas_datas_seguras",
    "trg_entrevistas_exclusao_segura",
    "trg_avaliacoes_insercao_segura",
    "trg_avaliacoes_atualizacao_segura",
    "trg_avaliacoes_exclusao_segura",
    "trg_avaliacao_criterios_insercao_segura",
    "trg_avaliacao_criterios_atualizacao_segura",
    "trg_avaliacao_criterios_exclusao_segura"
)


def instalar_protecoes() -> None:
    """Instala triggers em uma transação sem alterar entrevistas ou notas existentes."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        for nome in TRIGGERS:
            cursor.execute(f"DROP TRIGGER IF EXISTS {nome}")

        # A identidade da entrevista deve ser preservada.
        cursor.execute(
            """
            CREATE TRIGGER trg_entrevistas_identidade_segura
            BEFORE UPDATE OF usuario_id, tipo_entrevista_id, perfil_profissional ON entrevistas
            WHEN NEW.usuario_id IS NOT OLD.usuario_id
              OR NEW.tipo_entrevista_id IS NOT OLD.tipo_entrevista_id
              OR NEW.perfil_profissional IS NOT OLD.perfil_profissional
            BEGIN
                SELECT RAISE(ABORT, 'Proprietário, tipo e perfil da entrevista são imutáveis.');
            END;
            """
        )

        # Datas históricas não podem ser reescritas.
        cursor.execute(
            """
            CREATE TRIGGER trg_entrevistas_datas_seguras
            BEFORE UPDATE OF data_inicio, data_fim ON entrevistas
            WHEN NEW.data_inicio IS NOT OLD.data_inicio
              OR (OLD.status <> 'em_andamento' AND NEW.data_fim IS NOT OLD.data_fim)
            BEGIN
                SELECT RAISE(ABORT, 'Datas históricas da entrevista são imutáveis.');
            END;
            """
        )

        # Valida as transições de estado e a publicação da pontuação.
        cursor.execute(
            """
            CREATE TRIGGER trg_entrevistas_estado_seguro
            BEFORE UPDATE OF status, pontuacao_final ON entrevistas
            WHEN NEW.status IS NOT OLD.status OR NEW.pontuacao_final IS NOT OLD.pontuacao_final
            BEGIN
                SELECT CASE WHEN NOT (
                    (OLD.status = 'em_andamento' AND NEW.status IN ('finalizada', 'cancelada')
                        AND NEW.pontuacao_final IS NULL)
                    OR (OLD.status IN ('finalizada', 'erro_analise') AND NEW.status = 'em_analise'
                        AND NEW.pontuacao_final IS NULL)
                    OR (OLD.status = 'em_analise' AND NEW.status = 'erro_analise'
                        AND NEW.pontuacao_final IS NULL)
                    OR (OLD.status = 'em_analise' AND NEW.status = 'avaliada'
                        AND NEW.pontuacao_final BETWEEN 0 AND 10)
                ) THEN RAISE(ABORT, 'Transição de estado ou alteração de nota não permitida.') END;

                SELECT CASE WHEN NEW.status = 'finalizada' AND (
                    NEW.data_fim IS NULL
                    OR (OLD.perfil_profissional IS NOT NULL AND (
                        (SELECT COUNT(*) FROM entrevista_perguntas WHERE entrevista_id = OLD.id) <> 8
                        OR (SELECT COUNT(*) FROM respostas WHERE entrevista_id = OLD.id) <> 8
                        OR EXISTS (
                            SELECT 1 FROM entrevista_perguntas ep
                            WHERE ep.entrevista_id = OLD.id AND NOT EXISTS (
                                SELECT 1 FROM respostas r
                                WHERE r.entrevista_id = ep.entrevista_id AND r.pergunta_id = ep.pergunta_id
                            )
                        )
                        OR (SELECT COUNT(DISTINCT ordem_pergunta_aplicada) FROM entrevista_perguntas WHERE entrevista_id = OLD.id) <> 8
                        OR (SELECT MIN(ordem_pergunta_aplicada) FROM entrevista_perguntas WHERE entrevista_id = OLD.id) <> 1
                        OR (SELECT MAX(ordem_pergunta_aplicada) FROM entrevista_perguntas WHERE entrevista_id = OLD.id) <> 8
                        OR (SELECT COUNT(*) FROM entrevista_perguntas WHERE entrevista_id = OLD.id AND dificuldade_aplicada = 'basica') <>
                            CASE OLD.perfil_profissional WHEN 'estagio_trainee' THEN 5 WHEN 'junior' THEN 3 WHEN 'pleno' THEN 1 ELSE 0 END
                        OR (SELECT COUNT(*) FROM entrevista_perguntas WHERE entrevista_id = OLD.id AND dificuldade_aplicada = 'intermediaria') <>
                            CASE OLD.perfil_profissional WHEN 'estagio_trainee' THEN 3 WHEN 'junior' THEN 4 WHEN 'pleno' THEN 4 ELSE 3 END
                        OR (SELECT COUNT(*) FROM entrevista_perguntas WHERE entrevista_id = OLD.id AND dificuldade_aplicada = 'avancada') <>
                            CASE OLD.perfil_profissional WHEN 'estagio_trainee' THEN 0 WHEN 'junior' THEN 1 WHEN 'pleno' THEN 3 ELSE 5 END
                    ))
                    OR (OLD.perfil_profissional IS NULL AND NOT EXISTS (
                        SELECT 1 FROM respostas WHERE entrevista_id = OLD.id
                    ))
                ) THEN RAISE(ABORT, 'Não é possível finalizar uma entrevista incompleta.') END;

                SELECT CASE WHEN NEW.status = 'em_analise' AND (
                    (SELECT COUNT(*) FROM avaliacoes a INNER JOIN respostas r ON r.id = a.resposta_id
                        WHERE r.entrevista_id = OLD.id) > 0
                    OR (SELECT COUNT(*) FROM respostas WHERE entrevista_id = OLD.id) = 0
                    OR (OLD.perfil_profissional IS NOT NULL AND
                        (SELECT COUNT(*) FROM respostas WHERE entrevista_id = OLD.id) <> 8)
                ) THEN RAISE(ABORT, 'A entrevista não pode iniciar análise com dados inconsistentes.') END;

                SELECT CASE WHEN NEW.status = 'avaliada' AND (
                    (SELECT COUNT(*) FROM respostas WHERE entrevista_id = OLD.id) = 0
                    OR EXISTS (
                        SELECT 1 FROM respostas r
                        WHERE r.entrevista_id = OLD.id AND NOT EXISTS (
                            SELECT 1 FROM avaliacoes a WHERE a.resposta_id = r.id
                            AND a.pontuacao BETWEEN 0 AND 10
                            AND EXISTS (
                                SELECT 1 FROM avaliacao_criterios ac WHERE ac.avaliacao_id = a.id
                            )
                        )
                    )
                ) THEN RAISE(ABORT, 'Todas as respostas precisam de avaliações completas.') END;
            END;
            """
        )

        # Entrevistas concluídas não podem ser excluídas diretamente.
        cursor.execute(
            """
            CREATE TRIGGER trg_entrevistas_exclusao_segura
            BEFORE DELETE ON entrevistas
            WHEN OLD.status <> 'em_andamento'
            BEGIN
                SELECT RAISE(ABORT, 'Uma entrevista concluída não pode ser excluída diretamente.');
            END;
            """
        )

        # Avaliações individuais: somente durante em_analise.
        cursor.execute(
            """
            CREATE TRIGGER trg_avaliacoes_insercao_segura
            BEFORE INSERT ON avaliacoes
            WHEN COALESCE((
                SELECT e.status FROM respostas r
                INNER JOIN entrevistas e ON e.id = r.entrevista_id
                WHERE r.id = NEW.resposta_id
            ), '') <> 'em_analise'
            BEGIN
                SELECT RAISE(ABORT, 'A avaliação só pode ser registrada durante a análise.');
            END;
            """
        )

        cursor.execute(
            """
            CREATE TRIGGER trg_avaliacoes_atualizacao_segura
            BEFORE UPDATE ON avaliacoes
            WHEN NEW.resposta_id IS NOT OLD.resposta_id OR
                COALESCE((
                    SELECT e.status FROM respostas r
                    INNER JOIN entrevistas e ON e.id = r.entrevista_id
                    WHERE r.id = OLD.resposta_id
                ), '') <> 'em_analise'
            BEGIN
                SELECT RAISE(ABORT, 'A avaliação publicada é imutável.');
            END;
            """
        )

        # A limpeza de avaliações parciais é permitida também em erro_analise.
        cursor.execute(
            """
            CREATE TRIGGER trg_avaliacoes_exclusao_segura
            BEFORE DELETE ON avaliacoes
            WHEN COALESCE((
                SELECT e.status FROM respostas r
                INNER JOIN entrevistas e ON e.id = r.entrevista_id
                WHERE r.id = OLD.resposta_id
            ), '') NOT IN ('em_analise', 'erro_analise')
            BEGIN
                SELECT RAISE(ABORT, 'A avaliação publicada não pode ser excluída.');
            END;
            """
        )

        # As notas de cada critério seguem as restrições da avaliação.
        cursor.execute(
            """
            CREATE TRIGGER trg_avaliacao_criterios_insercao_segura
            BEFORE INSERT ON avaliacao_criterios
            WHEN COALESCE((
                SELECT e.status FROM avaliacoes a
                INNER JOIN respostas r ON r.id = a.resposta_id
                INNER JOIN entrevistas e ON e.id = r.entrevista_id
                WHERE a.id = NEW.avaliacao_id
            ), '') <> 'em_analise'
            BEGIN
                SELECT RAISE(ABORT, 'Notas dos critérios só podem ser inseridas durante a análise.');
            END;
            """
        )

        cursor.execute(
            """
            CREATE TRIGGER trg_avaliacao_criterios_atualizacao_segura
            BEFORE UPDATE ON avaliacao_criterios
            WHEN NEW.avaliacao_id IS NOT OLD.avaliacao_id OR
                COALESCE((
                    SELECT e.status FROM avaliacoes a
                    INNER JOIN respostas r ON r.id = a.resposta_id
                    INNER JOIN entrevistas e ON e.id = r.entrevista_id
                    WHERE a.id = OLD.avaliacao_id
                ), '') <> 'em_analise'
            BEGIN
                SELECT RAISE(ABORT, 'Notas dos critérios publicadas são imutáveis.');
            END;
            """
        )

        cursor.execute(
            """
            CREATE TRIGGER trg_avaliacao_criterios_exclusao_segura
            BEFORE DELETE ON avaliacao_criterios
            WHEN COALESCE((
                SELECT e.status FROM avaliacoes a
                INNER JOIN respostas r ON r.id = a.resposta_id
                INNER JOIN entrevistas e ON e.id = r.entrevista_id
                WHERE a.id = OLD.avaliacao_id
            ), '') NOT IN ('em_analise', 'erro_analise')
            BEGIN
                SELECT RAISE(ABORT, 'Notas dos critérios publicadas não podem ser excluídas.');
            END;
            """
        )

        # Confere a consistência do banco antes de confirmar a instalação.
        cursor.execute("PRAGMA foreign_key_check")

        if cursor.fetchone() is not None:
            raise sqlite3.IntegrityError("Há referências inválidas no banco.")

        cursor.execute("PRAGMA integrity_check")

        if cursor.fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("Falha na verificação de integridade do SQLite.")

        conexao.commit()
        print("Proteções das avaliações instaladas com sucesso.")

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


if __name__ == "__main__":
    instalar_protecoes()
