"""Funções responsáveis pela análise das respostas com MOCK_OPENAI ou OpenAI."""

import json
import os
import sqlite3
from typing import Any

from openai import OpenAI

try:
    from .avaliacao import processar_avaliacao
    from .database import conectar_banco
except ImportError:
    from avaliacao import processar_avaliacao
    from database import conectar_banco

# Configurações usadas pela análise. Durante o desenvolvimento o projeto continua usando MOCK_OPENAI=true.
MODELO_OPENAI = os.getenv("OPENAI_MODEL", "gpt-6-luna")
NOTA_MINIMA = 0.0
NOTA_MAXIMA = 10.0
MOCK_OPENAI = os.getenv("MOCK_OPENAI", "false").strip().lower() in ("1", "true", "yes", "sim")


def _validar_id(valor: int, campo: str) -> None:
    """Confere se um identificador é inteiro e maior que zero."""
    if not isinstance(valor, int) or valor <= 0:
        raise ValueError(f"{campo} inválido.")


def criar_cliente_openai() -> OpenAI:
    """Cria o cliente da OpenAI somente quando o modo MOCK estiver desativado."""
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("A variável OPENAI_API_KEY não foi configurada.")

    return OpenAI(api_key=api_key)


def obter_nome_modelo_avaliacao() -> str:
    """Retorna o nome que será salvo no campo do modelo usado na avaliação."""
    if MOCK_OPENAI:
        return "MOCK_OPENAI"

    return MODELO_OPENAI


def buscar_criterios_ativos() -> list[dict]:
    """Busca os critérios ativos que serão usados em uma análise."""
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
        criterios = []

        # Valida e monta uma lista simples que poderá ser reutilizada em todas as respostas.
        for registro in registros:
            peso = registro["peso"]

            if peso is None:
                raise ValueError("Existe critério ativo sem peso definido.")

            if float(peso) < 0:
                raise ValueError("Existe critério ativo com peso negativo.")

            criterios.append({
                "id": registro["id"],
                "nome": registro["nome"],
                "descricao": registro["descricao"],
                "peso": float(peso),
                "ordem": registro["ordem"]
            })

        return criterios
    finally:
        conexao.close()


def buscar_dados_resposta(resposta_id: int) -> dict | None:
    """Recupera a resposta usando somente os snapshots históricos necessários para a análise."""
    _validar_id(resposta_id, "ID da resposta")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT
                r.id AS resposta_id,
                r.entrevista_id,
                r.pergunta_id,
                r.texto_resposta,
                r.tempo_resposta,
                r.data_resposta,
                r.pergunta_texto_aplicado AS pergunta,
                r.exemplo_esperado_aplicado AS exemplo_esperado,
                r.competencia_id_aplicada AS competencia_id,
                r.competencia_nome_aplicada AS competencia,
                r.peso_pergunta_aplicado AS peso_pergunta,
                r.usa_star_aplicado AS usa_star,
                r.ordem_pergunta_aplicada AS ordem_pergunta,
                e.tipo_entrevista_id,
                e.tipo_entrevista_nome_aplicado AS tipo_entrevista,
                e.tipo_entrevista_descricao_aplicada AS tipo_entrevista_descricao,
                e.area_tecnica_id,
                e.area_tecnica_nome_aplicado AS area_tecnica,
                e.subarea_tecnica_id,
                e.subarea_tecnica_nome_aplicado AS subarea_tecnica
            FROM respostas r
            INNER JOIN entrevistas e ON e.id = r.entrevista_id
            WHERE r.id = ?
            """,
            (resposta_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            return None

        # Uma análise histórica não deve reconstruir informações usando os cadastros atuais.
        if registro["pergunta"] is None:
            raise ValueError("A resposta não possui o snapshot histórico da pergunta.")

        if registro["competencia_id"] is None:
            raise ValueError("A resposta não possui o snapshot histórico da competência.")

        if registro["competencia"] is None:
            raise ValueError("A resposta não possui o nome histórico da competência.")

        if registro["peso_pergunta"] is None:
            raise ValueError("A resposta não possui o peso histórico da pergunta.")

        if registro["usa_star"] is None:
            raise ValueError("A resposta não possui a configuração histórica do método STAR.")

        if registro["tipo_entrevista"] is None:
            raise ValueError("A entrevista não possui o snapshot histórico do tipo de entrevista.")

        return {
            "resposta_id": registro["resposta_id"],
            "entrevista_id": registro["entrevista_id"],
            "pergunta_id": registro["pergunta_id"],
            "pergunta": registro["pergunta"],
            "exemplo_esperado": registro["exemplo_esperado"],
            "competencia_id": registro["competencia_id"],
            "competencia": registro["competencia"],
            "peso_pergunta": registro["peso_pergunta"],
            "usa_star": bool(registro["usa_star"]),
            "ordem_pergunta": registro["ordem_pergunta"],
            "resposta": registro["texto_resposta"],
            "tempo_resposta": registro["tempo_resposta"],
            "data_resposta": registro["data_resposta"],
            "tipo_entrevista_id": registro["tipo_entrevista_id"],
            "tipo_entrevista": registro["tipo_entrevista"],
            "tipo_entrevista_descricao": registro["tipo_entrevista_descricao"],
            "area_tecnica_id": registro["area_tecnica_id"],
            "area_tecnica": registro["area_tecnica"],
            "subarea_tecnica_id": registro["subarea_tecnica_id"],
            "subarea_tecnica": registro["subarea_tecnica"]
        }
    finally:
        conexao.close()


def construir_rubrica(criterios: list[dict]) -> str:
    """Monta em texto a lista de critérios que será enviada para a avaliação."""
    linhas = []

    for criterio in criterios:
        descricao = criterio["descricao"] or "Sem descrição adicional."
        linhas.append(f"- {criterio['nome']}: {descricao}")

    return "\n".join(linhas)


def construir_prompt(dados: dict, criterios: list[dict]) -> str:
    """Monta o texto completo enviado para a avaliação de uma resposta."""
    rubrica = construir_rubrica(criterios)

    # O tipo sempre aparece. Área e subárea são incluídas somente quando existem no snapshot.
    linhas_contexto = [f"TIPO DE ENTREVISTA:\n{dados['tipo_entrevista']}"]

    if dados.get("area_tecnica"):
        linhas_contexto.append(f"ÁREA TÉCNICA:\n{dados['area_tecnica']}")

    if dados.get("subarea_tecnica"):
        linhas_contexto.append(f"SUBÁREA TÉCNICA:\n{dados['subarea_tecnica']}")

    contexto = "\n\n".join(linhas_contexto)

    # Acrescenta a orientação do método STAR somente quando a pergunta foi cadastrada com essa regra.
    if dados["usa_star"]:
        star = """
A pergunta foi cadastrada com utilização do método STAR.

Ao avaliar, considere se a resposta apresenta,
quando aplicável:

- Situação;
- Tarefa;
- Ação;
- Resultado.

Não penalize de maneira mecânica a ausência dos
nomes dessas etapas. Avalie se os elementos estão
presentes no conteúdo da resposta.
""".strip()
    else:
        star = """
A pergunta não exige obrigatoriamente a utilização
do método STAR.
""".strip()

    # A referência ajuda na avaliação, mas não deve ser tratada como resposta única correta.
    if dados.get("exemplo_esperado"):
        exemplo = f"""
REFERÊNCIA DE RESPOSTA ESPERADA:

{dados['exemplo_esperado']}

A referência serve apenas como apoio de avaliação.

Não exija reprodução literal e não considere
apenas respostas idênticas à referência como corretas.
""".strip()
    else:
        exemplo = """
Não existe exemplo de resposta esperado cadastrado
para esta pergunta.
""".strip()

    return f"""
Você está avaliando a resposta de um estudante em um
simulador educacional de entrevistas profissionais.

O objetivo é fornecer uma avaliação construtiva,
objetiva e útil para o desenvolvimento profissional.

{contexto}


COMPETÊNCIA AVALIADA:

{dados['competencia']}


PERGUNTA:

{dados['pergunta']}


RESPOSTA DO ESTUDANTE:

{dados['resposta']}


CRITÉRIOS:

{rubrica}


ESCALA:

Utilize notas entre 0.0 e 10.0.

0.0 até 2.0
Muito insuficiente.

2.1 até 4.0
Insuficiente.

4.1 até 6.0
Parcialmente adequada.

6.1 até 8.0
Adequada, apresentando oportunidades de melhoria.

8.1 até 9.0
Muito adequada.

9.1 até 10.0
Excepcionalmente bem desenvolvida.


REGRAS IMPORTANTES:

Avalie cada critério separadamente.

Considere o tipo de entrevista informado.

Quando houver área e subárea técnica, utilize esse
contexto para interpretar adequadamente a pergunta
e a resposta.

Não invente experiências, conhecimentos ou
informações não presentes na resposta.

Não presuma informações ausentes.

Fundamente a avaliação exclusivamente no conteúdo
fornecido.

Produza observações curtas e objetivas.

O feedback deve possuir finalidade educacional.

{star}

{exemplo}

Produza:

- nota para cada critério;
- justificativa curta para cada nota;
- pontos fortes;
- pontos de melhoria;
- feedback geral.
""".strip()


def construir_schema(criterios: list[dict]) -> dict:
    """Cria o JSON Schema esperado para o retorno estruturado da avaliação."""
    propriedades_criterios = {}
    nomes_criterios = []

    # Cada critério recebe nota e observação no objeto final.
    for criterio in criterios:
        nome = criterio["nome"]
        nomes_criterios.append(nome)
        propriedades_criterios[nome] = {
            "type": "object",
            "properties": {
                "nota": {
                    "type": "number",
                    "minimum": NOTA_MINIMA,
                    "maximum": NOTA_MAXIMA
                },
                "observacao": {"type": "string"}
            },
            "required": ["nota", "observacao"],
            "additionalProperties": False
        }

    return {
        "type": "object",
        "properties": {
            "criterios": {
                "type": "object",
                "properties": propriedades_criterios,
                "required": nomes_criterios,
                "additionalProperties": False
            },
            "pontos_fortes": {
                "type": "array",
                "items": {"type": "string"}
            },
            "pontos_melhoria": {
                "type": "array",
                "items": {"type": "string"}
            },
            "feedback": {"type": "string"}
        },
        "required": ["criterios", "pontos_fortes", "pontos_melhoria", "feedback"],
        "additionalProperties": False
    }


def gerar_resultado_mock(criterios: list[dict]) -> dict:
    """Gera uma avaliação simulada com a mesma estrutura usada pelo modo real."""
    criterios_mock = {}
    notas_mock = [8.0, 7.5, 8.5, 7.0, 9.0]

    # Repete a sequência de notas quando existirem mais critérios que valores na lista.
    for indice, criterio in enumerate(criterios):
        nome = criterio["nome"]
        nota = notas_mock[indice % len(notas_mock)]
        criterios_mock[nome] = {
            "nota": nota,
            "observacao": f"Avaliação simulada pelo modo MOCK_OPENAI para o critério {nome}."
        }

    return {
        "criterios": criterios_mock,
        "pontos_fortes": [
            "A resposta apresenta conteúdo relacionado à pergunta.",
            "A resposta possui estrutura compreensível."
        ],
        "pontos_melhoria": [
            "A resposta pode apresentar exemplos mais específicos.",
            "Os resultados das ações podem ser descritos com maior detalhamento."
        ],
        "feedback": (
            "Avaliação simulada para fins de teste. A resposta apresenta estrutura adequada e relação com a pergunta. "
            "Para melhorar, podem ser utilizados exemplos mais concretos, com maior detalhamento das ações realizadas "
            "e dos resultados alcançados. Este feedback foi produzido pelo modo MOCK_OPENAI e não representa uma "
            "avaliação realizada pela OpenAI."
        )
    }


def chamar_openai(prompt: str, criterios: list[dict]) -> dict:
    """Executa a avaliação simulada ou chama a OpenAI quando o modo MOCK estiver desligado."""
    if MOCK_OPENAI:
        print("[MOCK_OPENAI] Gerando avaliação simulada. Nenhuma chamada externa será realizada.")
        return gerar_resultado_mock(criterios)

    # No modo real, monta o schema e solicita um retorno estruturado.
    cliente = criar_cliente_openai()
    schema = construir_schema(criterios)

    resposta = cliente.responses.create(
        model=MODELO_OPENAI,
        instructions=(
            "Você é um avaliador educacional especializado em entrevistas profissionais. "
            "Siga rigorosamente os critérios fornecidos e produza somente a estrutura solicitada."
        ),
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "avaliacao_entrevista",
                "strict": True,
                "schema": schema
            }
        }
    )

    texto = resposta.output_text

    if not texto:
        raise RuntimeError("A OpenAI não retornou conteúdo para a análise.")

    try:
        return json.loads(texto)
    except json.JSONDecodeError as erro:
        raise RuntimeError("A resposta retornada pela OpenAI não contém JSON válido.") from erro


def validar_resultado(resultado: Any, criterios: list[dict]) -> dict:
    """Confere se o resultado da análise possui todos os campos e notas válidas."""
    if not isinstance(resultado, dict):
        raise ValueError("Resultado da análise inválido.")

    if "criterios" not in resultado:
        raise ValueError("Critérios não encontrados no resultado.")

    avaliacoes = resultado["criterios"]

    if not isinstance(avaliacoes, dict):
        raise ValueError("O campo criterios é inválido.")

    # Confere cada critério que deveria existir no retorno.
    for criterio in criterios:
        nome = criterio["nome"]

        if nome not in avaliacoes:
            raise ValueError(f"Critério ausente: {nome}")

        dados = avaliacoes[nome]

        if not isinstance(dados, dict):
            raise ValueError(f"A avaliação do critério {nome} é inválida.")

        try:
            nota = float(dados["nota"])
        except (KeyError, TypeError, ValueError) as erro:
            raise ValueError(f"Nota inválida para o critério {nome}.") from erro

        if nota < NOTA_MINIMA or nota > NOTA_MAXIMA:
            raise ValueError(f"A nota de {nome} deve estar entre 0 e 10.")

        dados["nota"] = nota
        observacao = dados.get("observacao")

        if not isinstance(observacao, str):
            raise ValueError(f"Observação inválida para {nome}.")

    # Os campos de lista precisam conter somente textos.
    for campo in ("pontos_fortes", "pontos_melhoria"):
        valor = resultado.get(campo)

        if not isinstance(valor, list):
            raise ValueError(f"O campo {campo} deve ser uma lista.")

        for item in valor:
            if not isinstance(item, str):
                raise ValueError(f"Todos os itens de {campo} devem ser textos.")

    if not isinstance(resultado.get("feedback"), str):
        raise ValueError("O feedback retornado é inválido.")

    return resultado


def calcular_pontuacao_resposta(resultado: dict, criterios: list[dict]) -> float:
    """Calcula a média ponderada da resposta usando os pesos dos critérios aplicados."""
    soma_pesos = 0.0

    for criterio in criterios:
        soma_pesos += criterio["peso"]

    if soma_pesos <= 0:
        raise ValueError("A soma dos pesos deve ser maior que zero.")

    pontuacao = 0.0

    for criterio in criterios:
        nome = criterio["nome"]
        nota = resultado["criterios"][nome]["nota"]
        peso = criterio["peso"]
        pontuacao += nota * peso

    pontuacao /= soma_pesos
    return round(pontuacao, 2)


def salvar_avaliacao(resposta_id: int, resultado: dict, criterios: list[dict]) -> int:
    """Salva a avaliação e congela os dados históricos de cada critério aplicado."""
    _validar_id(resposta_id, "ID da resposta")
    pontuacao = calcular_pontuacao_resposta(resultado, criterios)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        # A resposta precisa existir e ainda não pode possuir avaliação.
        cursor.execute("SELECT id FROM respostas WHERE id = ?", (resposta_id,))

        if cursor.fetchone() is None:
            raise ValueError("Resposta não encontrada.")

        cursor.execute(
            "SELECT id FROM avaliacoes WHERE resposta_id = ? LIMIT 1",
            (resposta_id,)
        )

        if cursor.fetchone() is not None:
            raise ValueError("Esta resposta já possui avaliação.")

        pontos_fortes = json.dumps(resultado["pontos_fortes"], ensure_ascii=False)
        pontos_melhoria = json.dumps(resultado["pontos_melhoria"], ensure_ascii=False)
        modelo_utilizado = obter_nome_modelo_avaliacao()

        # Salva a avaliação principal da resposta.
        cursor.execute(
            """
            INSERT INTO avaliacoes (
                resposta_id,
                pontuacao,
                pontos_fortes,
                pontos_melhoria,
                feedback,
                modelo_ia
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                resposta_id,
                pontuacao,
                pontos_fortes,
                pontos_melhoria,
                resultado["feedback"],
                modelo_utilizado
            )
        )
        avaliacao_id = int(cursor.lastrowid)

        # Cada nota recebe também os dados históricos do critério usado naquela avaliação.
        for criterio in criterios:
            nome = criterio["nome"]
            dados = resultado["criterios"][nome]

            cursor.execute(
                """
                INSERT INTO avaliacao_criterios (
                    avaliacao_id,
                    criterio_id,
                    nota,
                    observacao,
                    peso_aplicado,
                    criterio_nome_aplicado,
                    criterio_descricao_aplicada,
                    criterio_ordem_aplicada
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    avaliacao_id,
                    criterio["id"],
                    dados["nota"],
                    dados["observacao"],
                    criterio["peso"],
                    criterio["nome"],
                    criterio["descricao"],
                    criterio["ordem"]
                )
            )

        conexao.commit()
        return avaliacao_id

    except sqlite3.IntegrityError as erro:
        conexao.rollback()
        mensagem = str(erro).lower()

        if "unique constraint failed" in mensagem:
            raise ValueError("Esta resposta já possui avaliação.") from erro

        raise
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def analisar_resposta(resposta_id: int, criterios: list[dict] | None = None) -> int:
    """Analisa uma resposta usando os critérios recebidos ou os critérios ativos atuais."""
    dados = buscar_dados_resposta(resposta_id)

    if dados is None:
        raise ValueError("Resposta não encontrada.")

    # Na análise completa da entrevista, a mesma lista é recebida para todas as respostas.
    if criterios is None:
        criterios = buscar_criterios_ativos()

    if not criterios:
        raise ValueError("Nenhum critério ativo encontrado.")

    prompt = construir_prompt(dados, criterios)
    resultado = chamar_openai(prompt, criterios)
    resultado = validar_resultado(resultado, criterios)
    return salvar_avaliacao(resposta_id, resultado, criterios)


def buscar_respostas_entrevista(entrevista_id: int) -> list[int]:
    """Retorna os IDs das respostas seguindo a ordem histórica das perguntas."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT r.id
            FROM respostas r
            WHERE r.entrevista_id = ?
            ORDER BY COALESCE(r.ordem_pergunta_aplicada, 999999), r.id
            """,
            (entrevista_id,)
        )
        registros = cursor.fetchall()
        respostas = []

        for registro in registros:
            respostas.append(registro["id"])

        return respostas
    finally:
        conexao.close()


def _alterar_status(entrevista_id: int, novo_status: str) -> None:
    """Atualiza diretamente o status de uma entrevista."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "UPDATE entrevistas SET status = ? WHERE id = ?",
            (novo_status, entrevista_id)
        )

        if cursor.rowcount == 0:
            raise ValueError("Entrevista não encontrada.")

        conexao.commit()
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _adquirir_entrevista_para_analise(entrevista_id: int) -> None:
    """Reserva a entrevista para impedir duas análises simultâneas."""
    _validar_id(entrevista_id, "ID da entrevista")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT id, status FROM entrevistas WHERE id = ?",
            (entrevista_id,)
        )
        entrevista = cursor.fetchone()

        if entrevista is None:
            raise ValueError("Entrevista não encontrada.")

        if entrevista["status"] not in ("finalizada", "erro_analise"):
            raise ValueError("A entrevista precisa estar finalizada antes da análise.")

        # Em nova tentativa depois de erro, remove qualquer resultado parcial anterior.
        if entrevista["status"] == "erro_analise":
            cursor.execute(
                """
                DELETE FROM avaliacoes
                WHERE resposta_id IN (
                    SELECT id
                    FROM respostas
                    WHERE entrevista_id = ?
                )
                """,
                (entrevista_id,)
            )
            cursor.execute(
                "UPDATE entrevistas SET pontuacao_final = NULL WHERE id = ?",
                (entrevista_id,)
            )

        # O WHERE garante que somente uma chamada consiga mudar o status para em_analise.
        cursor.execute(
            """
            UPDATE entrevistas
            SET status = 'em_analise'
            WHERE id = ? AND status IN ('finalizada', 'erro_analise')
            """,
            (entrevista_id,)
        )

        if cursor.rowcount != 1:
            raise ValueError("A entrevista já está sendo analisada ou não está disponível para análise.")

        conexao.commit()

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _limpar_analise_parcial(entrevista_id: int) -> None:
    """Remove avaliações parciais e marca a entrevista com erro quando a análise falha."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        # Exclui avaliações das respostas da entrevista. As notas por critério são removidas pelo relacionamento do banco.
        cursor.execute(
            """
            DELETE FROM avaliacoes
            WHERE resposta_id IN (
                SELECT id
                FROM respostas
                WHERE entrevista_id = ?
            )
            """,
            (entrevista_id,)
        )

        cursor.execute(
            """
            UPDATE entrevistas
            SET status = 'erro_analise', pontuacao_final = NULL
            WHERE id = ?
            """,
            (entrevista_id,)
        )
        conexao.commit()

    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def analisar_entrevista(entrevista_id: int) -> dict:
    """Analisa todas as respostas de uma entrevista finalizada e calcula o resultado final."""
    _validar_id(entrevista_id, "ID da entrevista")

    # Primeiro muda atomicamente o status para impedir análises concorrentes.
    _adquirir_entrevista_para_analise(entrevista_id)

    try:
        # Os critérios são buscados uma única vez e usados em todas as respostas da entrevista.
        criterios = buscar_criterios_ativos()

        if not criterios:
            raise ValueError("Nenhum critério ativo encontrado.")

        respostas = buscar_respostas_entrevista(entrevista_id)

        if not respostas:
            raise ValueError("A entrevista não possui respostas.")

        avaliacoes = []

        # Analisa cada resposta usando exatamente o mesmo conjunto de critérios.
        for resposta_id in respostas:
            avaliacao_id = analisar_resposta(resposta_id, criterios=criterios)
            avaliacoes.append(avaliacao_id)

        # O motor de pontuação calcula a nota final e altera a entrevista para avaliada.
        resultado_final = processar_avaliacao(entrevista_id)

        return {
            "entrevista_id": entrevista_id,
            "modo_analise": "mock" if MOCK_OPENAI else "openai",
            "modelo": obter_nome_modelo_avaliacao(),
            "quantidade_criterios_aplicados": len(criterios),
            "avaliacoes": avaliacoes,
            "resultado_final": resultado_final
        }

    except Exception:
        # Qualquer falha precisa retirar resultados incompletos antes de propagar o erro.
        _limpar_analise_parcial(entrevista_id)
        raise