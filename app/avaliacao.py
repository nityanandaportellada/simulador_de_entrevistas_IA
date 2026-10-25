
"""Motor de pontuação usado para consolidar as avaliações das entrevistas."""

import sqlite3
import math

try:
    from .database import conectar_banco
except ImportError:
    from database import conectar_banco

NOTA_MINIMA = 0.0
NOTA_MAXIMA = 10.0

CLASSIFICACOES = (
    (0.0, 4.9, "Necessita desenvolvimento"),
    (5.0, 6.9, "Regular"),
    (7.0, 8.4, "Bom"),
    (8.5, 10.0, "Muito bom")
)


def _validar_id(valor: int, nome: str) -> None:
    """Confere se um identificador é inteiro e maior que zero."""
    if type(valor) is not int or valor <= 0:
        raise ValueError(f"{nome} inválido.")


def _validar_nota(valor, nome: str = "Nota") -> float:
    """Converte uma nota para float e exige um valor entre 0 e 10."""
    if isinstance(valor, bool):
        raise ValueError(f"{nome} inválida.")
    try:
        nota = float(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"{nome} inválida.") from erro

    if not math.isfinite(nota) or nota < NOTA_MINIMA or nota > NOTA_MAXIMA:
        raise ValueError(f"{nome} deve ser finita e estar entre 0 e 10.")

    return nota


def _validar_peso(valor, nome: str) -> float:
    """Converte e valida um peso histórico, permitindo zero mas não valores negativos."""
    if valor is None:
        raise ValueError(f"{nome} não informado.")

    if isinstance(valor, bool):
        raise ValueError(f"{nome} inválido.")
    try:
        peso = float(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"{nome} inválido.") from erro

    if not math.isfinite(peso) or peso < 0:
        raise ValueError(f"{nome} deve ser finito e não negativo.")

    return peso


def buscar_entrevista(entrevista_id: int) -> dict | None:
    """Busca a entrevista usando os snapshots históricos de tipo, área e subárea."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                usuario_id,
                tipo_entrevista_id,
                tipo_entrevista_nome_aplicado,
                tipo_entrevista_descricao_aplicada,
                area_tecnica_id,
                area_tecnica_nome_aplicado,
                subarea_tecnica_id,
                subarea_tecnica_nome_aplicado,
                data_inicio,
                data_fim,
                status,
                pontuacao_final,
                observacoes
            FROM entrevistas
            WHERE id = ?
            """,
            (entrevista_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            return None

        return {
            "id": registro["id"],
            "usuario_id": registro["usuario_id"],
            "tipo_entrevista_id": registro["tipo_entrevista_id"],
            "tipo_entrevista": registro["tipo_entrevista_nome_aplicado"],
            "tipo_entrevista_descricao": registro["tipo_entrevista_descricao_aplicada"],
            "area_tecnica_id": registro["area_tecnica_id"],
            "area_tecnica": registro["area_tecnica_nome_aplicado"],
            "subarea_tecnica_id": registro["subarea_tecnica_id"],
            "subarea_tecnica": registro["subarea_tecnica_nome_aplicado"],
            "data_inicio": registro["data_inicio"],
            "data_fim": registro["data_fim"],
            "status": registro["status"],
            "pontuacao_final": registro["pontuacao_final"],
            "observacoes": registro["observacoes"]
        }
    finally:
        conexao.close()


def buscar_criterios_ativos() -> list[dict]:
    """Lista os critérios atualmente ativos. Os cálculos históricos não dependem desses dados atuais."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id, nome, descricao, peso, ordem
            FROM criterios_avaliacao
            WHERE ativo = 1
            ORDER BY COALESCE(ordem, 999999), id
            """
        )
        registros = cursor.fetchall()

        return [
            {
                "id": registro["id"],
                "nome": registro["nome"],
                "descricao": registro["descricao"],
                "peso": registro["peso"],
                "ordem": registro["ordem"]
            }
            for registro in registros
        ]
    finally:
        conexao.close()


def buscar_avaliacoes_entrevista(entrevista_id: int) -> list[dict]:
    """Busca as avaliações da entrevista usando o peso histórico de cada pergunta."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT
                a.id,
                a.resposta_id,
                a.pontuacao,
                a.pontos_fortes,
                a.pontos_melhoria,
                a.feedback,
                a.modelo_ia,
                a.data_avaliacao,
                r.pergunta_id,
                r.peso_pergunta_aplicado AS peso_pergunta
            FROM avaliacoes a
            INNER JOIN respostas r ON r.id = a.resposta_id
            WHERE r.entrevista_id = ?
            ORDER BY COALESCE(r.ordem_pergunta_aplicada, 999999), r.id, a.id
            """,
            (entrevista_id,)
        )
        resultados = []

        # Valida os valores históricos antes de devolvê-los para os cálculos.
        for registro in cursor.fetchall():
            peso_pergunta = _validar_peso(
                registro["peso_pergunta"],
                "Peso histórico da pergunta"
            )

            pontuacao = registro["pontuacao"]

            if pontuacao is not None:
                pontuacao = _validar_nota(
                    pontuacao,
                    "Pontuação da resposta"
                )

            resultados.append({
                "id": registro["id"],
                "avaliacao_id": registro["id"],
                "resposta_id": registro["resposta_id"],
                "pergunta_id": registro["pergunta_id"],
                "pontuacao": pontuacao,
                "pontos_fortes": registro["pontos_fortes"],
                "pontos_melhoria": registro["pontos_melhoria"],
                "feedback": registro["feedback"],
                "modelo_ia": registro["modelo_ia"],
                "data_avaliacao": registro["data_avaliacao"],
                "peso_pergunta": peso_pergunta
            })

        return resultados
    finally:
        conexao.close()


def buscar_notas_criterios(entrevista_id: int) -> list[dict]:
    """Busca notas e snapshots dos critérios sem usar o cadastro administrativo atual."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT
                ac.avaliacao_id,
                ac.criterio_id,
                ac.nota,
                ac.observacao,
                ac.peso_aplicado AS peso_criterio,
                ac.criterio_nome_aplicado AS criterio,
                ac.criterio_descricao_aplicada AS criterio_descricao,
                ac.criterio_ordem_aplicada AS ordem_criterio,
                r.id AS resposta_id,
                r.pergunta_id,
                r.peso_pergunta_aplicado AS peso_pergunta
            FROM avaliacao_criterios ac
            INNER JOIN avaliacoes a ON a.id = ac.avaliacao_id
            INNER JOIN respostas r ON r.id = a.resposta_id
            WHERE r.entrevista_id = ?
            ORDER BY
                COALESCE(r.ordem_pergunta_aplicada, 999999),
                r.id,
                COALESCE(ac.criterio_ordem_aplicada, 999999),
                ac.criterio_id
            """,
            (entrevista_id,)
        )
        resultados = []

        for registro in cursor.fetchall():
            # Nome, nota e pesos históricos são obrigatórios para um cálculo confiável.
            if registro["criterio"] is None:
                raise ValueError(
                    "Existe nota sem nome histórico do critério."
                )

            nota = _validar_nota(
                registro["nota"],
                "Nota do critério"
            )

            peso_criterio = _validar_peso(
                registro["peso_criterio"],
                "Peso histórico do critério"
            )

            peso_pergunta = _validar_peso(
                registro["peso_pergunta"],
                "Peso histórico da pergunta"
            )

            resultados.append({
                "avaliacao_id": registro["avaliacao_id"],
                "resposta_id": registro["resposta_id"],
                "pergunta_id": registro["pergunta_id"],
                "criterio_id": registro["criterio_id"],
                "criterio": registro["criterio"],
                "criterio_descricao": registro["criterio_descricao"],
                "ordem_criterio": registro["ordem_criterio"],
                "nota": nota,
                "observacao": registro["observacao"],
                "peso_criterio": peso_criterio,
                "peso_pergunta": peso_pergunta
            })

        return resultados
    finally:
        conexao.close()


def contar_respostas(entrevista_id: int) -> int:
    """Conta todas as respostas existentes na entrevista."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM respostas
            WHERE entrevista_id = ?
            """,
            (entrevista_id,)
        )

        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def contar_respostas_avaliadas(entrevista_id: int) -> int:
    """Conta quantas respostas diferentes da entrevista já possuem avaliação."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(DISTINCT a.resposta_id) AS quantidade
            FROM avaliacoes a
            INNER JOIN respostas r ON r.id = a.resposta_id
            WHERE r.entrevista_id = ?
            """,
            (entrevista_id,)
        )

        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def entrevista_totalmente_avaliada(entrevista_id: int) -> bool:
    """Verifica se a entrevista possui respostas e se todas elas já foram avaliadas."""
    quantidade_respostas = contar_respostas(entrevista_id)
    quantidade_avaliadas = contar_respostas_avaliadas(entrevista_id)

    if quantidade_respostas == 0:
        return False

    return quantidade_respostas == quantidade_avaliadas


def calcular_pontuacao_resposta(avaliacao_id: int) -> float:
    """Calcula a nota da resposta usando somente notas e pesos históricos dos critérios."""
    _validar_id(avaliacao_id, "ID da avaliação")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT nota, peso_aplicado AS peso
            FROM avaliacao_criterios
            WHERE avaliacao_id = ?
            ORDER BY COALESCE(criterio_ordem_aplicada, 999999), criterio_id
            """,
            (avaliacao_id,)
        )
        registros = cursor.fetchall()

        if not registros:
            raise ValueError(
                "A avaliação não possui notas por critério."
            )

        soma_pesos = 0.0
        soma_ponderada = 0.0

        # Soma nota x peso e depois divide pela soma dos pesos.
        for registro in registros:
            nota = _validar_nota(
                registro["nota"],
                "Nota do critério"
            )

            peso = _validar_peso(
                registro["peso"],
                "Peso histórico do critério"
            )

            soma_ponderada += nota * peso
            soma_pesos += peso

        if soma_pesos <= 0:
            raise ValueError(
                "A soma dos pesos históricos dos critérios deve ser maior que zero."
            )

        return round(
            soma_ponderada / soma_pesos,
            2
        )
    finally:
        conexao.close()


def atualizar_pontuacoes_respostas(entrevista_id: int) -> None:
    """Recalcula todas as notas das respostas antes de atualizar o banco em uma única transação."""
    _validar_id(entrevista_id, "ID da entrevista")
    avaliacoes = buscar_avaliacoes_entrevista(entrevista_id)

    if not avaliacoes:
        raise ValueError(
            "A entrevista não possui avaliações."
        )

    pontuacoes = []

    # Calcula tudo antes para não deixar parte das avaliações atualizada em caso de erro histórico.
    for avaliacao in avaliacoes:
        avaliacao_id = avaliacao["avaliacao_id"]
        pontuacao = calcular_pontuacao_resposta(avaliacao_id)
        pontuacoes.append((pontuacao, avaliacao_id))

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT status FROM entrevistas WHERE id = ?", (entrevista_id,))
        entrevista = cursor.fetchone()
        if entrevista is None or entrevista["status"] != "em_analise":
            raise ValueError("As notas só podem ser consolidadas enquanto a entrevista estiver em análise.")

        for pontuacao, avaliacao_id in pontuacoes:
            cursor.execute(
                """
                UPDATE avaliacoes
                SET pontuacao = ?
                WHERE id = ?
                """,
                (pontuacao, avaliacao_id)
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    "Não foi possível atualizar uma das avaliações."
                )

        conexao.commit()
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def calcular_pontuacao_geral(entrevista_id: int) -> float:
    """Calcula a nota geral ponderando cada resposta pelo peso histórico de sua pergunta."""
    _validar_id(entrevista_id, "ID da entrevista")
    avaliacoes = buscar_avaliacoes_entrevista(entrevista_id)

    if not avaliacoes:
        raise ValueError(
            "A entrevista não possui avaliações."
        )

    soma_pesos = 0.0
    soma_ponderada = 0.0

    for avaliacao in avaliacoes:
        pontuacao = _validar_nota(
            avaliacao["pontuacao"],
            "Pontuação da resposta"
        )

        peso = _validar_peso(
            avaliacao["peso_pergunta"],
            "Peso histórico da pergunta"
        )

        soma_ponderada += pontuacao * peso
        soma_pesos += peso

    if soma_pesos <= 0:
        raise ValueError(
            "A soma dos pesos históricos das perguntas deve ser maior que zero."
        )

    return round(
        soma_ponderada / soma_pesos,
        2
    )


def calcular_desempenho_criterios(entrevista_id: int) -> list[dict]:
    """Calcula a média de cada critério ponderando as notas pelo peso histórico das perguntas."""
    _validar_id(entrevista_id, "ID da entrevista")
    notas = buscar_notas_criterios(entrevista_id)

    if not notas:
        raise ValueError(
            "Não existem notas de critérios para esta entrevista."
        )

    acumuladores = {}

    for registro in notas:
        criterio_id = registro["criterio_id"]

        # Na primeira ocorrência guarda os dados históricos que identificam o critério.
        if criterio_id not in acumuladores:
            acumuladores[criterio_id] = {
                "criterio_id": criterio_id,
                "criterio": registro["criterio"],
                "criterio_descricao": registro["criterio_descricao"],
                "ordem_criterio": registro["ordem_criterio"],
                "peso_criterio": registro["peso_criterio"],
                "soma": 0.0,
                "soma_pesos": 0.0,
                "quantidade": 0
            }
        else:
            # O mesmo critério deve manter exatamente o mesmo snapshot em toda a entrevista.
            dados_existentes = acumuladores[criterio_id]

            if (
                dados_existentes["criterio"] != registro["criterio"]
                or dados_existentes["criterio_descricao"] != registro["criterio_descricao"]
                or dados_existentes["ordem_criterio"] != registro["ordem_criterio"]
                or dados_existentes["peso_criterio"] != registro["peso_criterio"]
            ):
                raise ValueError(
                    "Foram encontrados snapshots históricos inconsistentes "
                    "para o mesmo critério dentro da entrevista."
                )

        peso_pergunta = _validar_peso(
            registro["peso_pergunta"],
            "Peso histórico da pergunta"
        )

        nota = _validar_nota(
            registro["nota"],
            "Nota do critério"
        )

        acumuladores[criterio_id]["soma"] += nota * peso_pergunta
        acumuladores[criterio_id]["soma_pesos"] += peso_pergunta
        acumuladores[criterio_id]["quantidade"] += 1

    resultados = []

    # Calcula a média final de cada critério.
    for dados in acumuladores.values():
        if dados["soma_pesos"] <= 0:
            raise ValueError(
                "A soma dos pesos históricos das perguntas deve ser maior que zero "
                "para calcular o desempenho do critério."
            )

        media = dados["soma"] / dados["soma_pesos"]

        resultados.append({
            "criterio_id": dados["criterio_id"],
            "criterio": dados["criterio"],
            "criterio_descricao": dados["criterio_descricao"],
            "ordem_criterio": dados["ordem_criterio"],
            "media": round(media, 2),
            "peso": dados["peso_criterio"],
            "quantidade_avaliacoes": dados["quantidade"]
        })

    resultados.sort(
        key=lambda item: (
            item["ordem_criterio"]
            if item["ordem_criterio"] is not None
            else 999999,
            item["criterio_id"]
        )
    )

    return resultados


def classificar_desempenho(pontuacao: float) -> str:
    """Transforma a pontuação final em uma das classificações usadas pelo sistema."""
    pontuacao = _validar_nota(
        pontuacao,
        "Pontuação"
    )

    if pontuacao < 5.0:
        return "Necessita desenvolvimento"

    if pontuacao < 7.0:
        return "Regular"

    if pontuacao < 8.5:
        return "Bom"

    return "Muito bom"


def identificar_destaques(desempenho_criterios: list[dict]) -> dict:
    """Identifica o critério com maior média e o critério com menor média."""
    if not desempenho_criterios:
        return {
            "melhor_criterio": None,
            "criterio_a_desenvolver": None
        }

    melhor = max(
        desempenho_criterios,
        key=lambda item: item["media"]
    )

    menor = min(
        desempenho_criterios,
        key=lambda item: item["media"]
    )

    return {
        "melhor_criterio": {
            "criterio": melhor["criterio"],
            "media": melhor["media"]
        },
        "criterio_a_desenvolver": {
            "criterio": menor["criterio"],
            "media": menor["media"]
        }
    }


def atualizar_resultado_entrevista(
    entrevista_id: int,
    pontuacao_final: float
) -> None:
    """Salva a pontuação final e muda o status da entrevista para avaliada."""
    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )

    pontuacao_final = _validar_nota(
        pontuacao_final,
        "Pontuação final"
    )

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        # A avaliação publicada não pode ser substituída por outra execução.
        cursor.execute(
            """UPDATE entrevistas SET pontuacao_final = ?, status = 'avaliada'
            WHERE id = ? AND status = 'em_analise'""", (pontuacao_final, entrevista_id)
        )
        if cursor.rowcount != 1:
            raise ValueError("A entrevista não está em análise ou já foi avaliada.")

        conexao.commit()
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def processar_avaliacao(entrevista_id: int) -> dict:
    """Executa todo o cálculo final da entrevista usando somente dados históricos."""
    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )

    entrevista = buscar_entrevista(
        entrevista_id
    )

    if entrevista is None:
        raise ValueError(
            "Entrevista não encontrada."
        )

    # A publicação é exclusiva da análise em andamento.
    # Não recalcula entrevistas já publicadas nem ignora a reserva do serviço de IA.
    if entrevista["status"] != "em_analise":
        raise ValueError("A entrevista precisa estar em análise para consolidar a pontuação.")

    if not entrevista_totalmente_avaliada(
        entrevista_id
    ):
        raise ValueError(
            "Nem todas as respostas da entrevista foram avaliadas."
        )

    # Primeiro recalcula as notas individuais e depois consolida o resultado da entrevista.
    atualizar_pontuacoes_respostas(
        entrevista_id
    )

    pontuacao_final = calcular_pontuacao_geral(
        entrevista_id
    )

    desempenho_criterios = calcular_desempenho_criterios(
        entrevista_id
    )

    classificacao = classificar_desempenho(
        pontuacao_final
    )

    destaques = identificar_destaques(
        desempenho_criterios
    )

    atualizar_resultado_entrevista(
        entrevista_id,
        pontuacao_final
    )

    return {
        "entrevista_id": entrevista_id,
        "tipo_entrevista": entrevista["tipo_entrevista"],
        "area_tecnica": entrevista["area_tecnica"],
        "subarea_tecnica": entrevista["subarea_tecnica"],
        "pontuacao_final": pontuacao_final,
        "classificacao": classificacao,
        "desempenho_criterios": desempenho_criterios,
        "melhor_criterio": destaques["melhor_criterio"],
        "criterio_a_desenvolver": destaques["criterio_a_desenvolver"]
    }
