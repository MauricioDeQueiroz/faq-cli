"""FAQ CLI — Modo RAG (Checkpoint A, Assignment 3).

Uso: python faq_rag.py "sua pergunta"
     python faq_rag.py "sua pergunta" --debug   (mostra o top-k completo com scores)

DECISÕES DE ARQUITETURA (registradas aqui de propósito, para o diagnóstico):
- Chunk = cada FAQ inteira (pergunta + resposta) é um único chunk. Não há
  subdivisão, porque o corpus é pequeno (20 itens) e subdividir não traria
  benefício real — isso também significa que, se o RAG errar, "chunking"
  dificilmente será a causa (ver relatorio_diagnostico.md).
- Embeddings: sentence-transformers, modelo multilíngue local
  "paraphrase-multilingual-MiniLM-L12-v2". Escolhido por não exigir API key
  nem custo por request — decisão tomada sob restrição de acesso à API da
  Anthropic no momento da implementação.
- Vector store: matriz numpy em memória + similaridade de cosseno. Não há
  necessidade de banco vetorial dedicado para 20 itens.
- Top-k = 3. Definido para permitir observar casos de ambiguidade (uma
  pergunta que compete entre 2-3 FAQs vizinhas), sem diluir demais o teste.

LIMITAÇÃO CONHECIDA E DECLARADA:
Esta versão NÃO chama um LLM para gerar a resposta final. Por indisponibilidade
temporária de acesso à API da Anthropic (bloqueio de organização), a etapa de
"geração" foi substituída por retorno direto do texto da FAQ mais similar,
com citação automática da fonte. Isso significa que, nesta versão, um erro só
pode ser diagnosticado como "retrieval" — a categoria "erro de geração" não é
testável até a etapa de geração via LLM ser adicionada (ver TODO no final do
arquivo e em avaliar.py).
"""

import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

import gemini_client

CAMINHO_FAQS = Path(__file__).resolve().parent / "data" / "faqs.json"
MODELO_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 3

SYSTEM_INSTRUCTION_GERACAO = (
    "Você é um assistente de atendimento ao cliente. Responda à pergunta do "
    "usuário usando APENAS as FAQs fornecidas abaixo como contexto. Regras:\n"
    "1. Cite explicitamente qual FAQ (pelo número) foi usada, no formato "
    "'Fonte: FAQ #N'.\n"
    "2. Se mais de uma FAQ fornecida for igualmente relevante, não escolha "
    "uma arbitrariamente — explique a ambiguidade e apresente as opções.\n"
    "3. Se nenhuma das FAQs fornecidas responder à pergunta, diga isso "
    "claramente em vez de forçar uma resposta.\n"
    "4. Seja objetivo e responda em português do Brasil."
)

# Limiar de similaridade de cosseno abaixo do qual consideramos "nada parecido
# o suficiente" (equivalente ao caso de pergunta fora do corpus).
#
# CALIBRADO com dados reais da avaliação: a pergunta inexistente de teste
# ("vagas de estágio") teve score de top-1 = 0.267, enquanto uma pergunta
# respondível de teste ("tela congelou") teve score de top-1 = 0.246 — ou
# seja, HÁ SOBREPOSIÇÃO entre os dois grupos com apenas 1 amostra "inexistente"
# disponível. Um limiar único não separa perfeitamente os dois casos.
#
# Decisão consciente: priorizamos evitar respostas erradas/forçadas sobre
# evitar falsos "não encontrei" (mais seguro para o usuário). Por isso o
# limiar precisa ficar ACIMA do score da pergunta inexistente (0.267) — não
# abaixo — para de fato rejeitá-la. Isso sacrifica como trade-off a pergunta
# legítima de score baixo (0.246), que também será classificada como "sem
# resposta". Essa limitação está documentada no relatório de diagnóstico.
LIMIAR_SEM_RESPOSTA = 0.28


def carregar_faqs(caminho):
    """Carrega a base de FAQs. Retorna None em caso de erro (sem stacktrace)."""
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: base de FAQs não encontrada em {caminho}.")
        return None
    except json.JSONDecodeError as e:
        print(f"Erro: base de FAQs está com JSON inválido ({e}).")
        return None


def texto_do_chunk(faq):
    """Monta o texto do chunk: pergunta + resposta concatenadas.

    Incluir a resposta no texto embedado (não só a pergunta) ajuda o retrieval
    a capturar perguntas do usuário que mencionam termos que só aparecem na
    resposta (ex.: "código" pode aparecer mais na resposta de 2FA do que na
    pergunta oficial da FAQ).
    """
    return f"{faq['pergunta']} {faq['resposta']}"


class IndiceRAG:
    """Índice em memória: embeddings das FAQs + busca por similaridade de cosseno."""

    def __init__(self, faqs, modelo_nome=MODELO_EMBEDDING):
        self.faqs = faqs
        self.modelo = SentenceTransformer(modelo_nome)
        textos = [texto_do_chunk(faq) for faq in faqs]
        embeddings = self.modelo.encode(textos, normalize_embeddings=True)
        self.embeddings = np.asarray(embeddings, dtype=np.float32)

    def buscar(self, pergunta, k=TOP_K):
        """Retorna os top-k (faq, score) ordenados por similaridade decrescente.

        Como os embeddings estão normalizados (normalize_embeddings=True), o
        produto escalar já é equivalente à similaridade de cosseno — não é
        necessário dividir pelas normas de novo.
        """
        vetor_pergunta = self.modelo.encode([pergunta], normalize_embeddings=True)[0]
        scores = self.embeddings @ vetor_pergunta  # produto escalar = cosseno
        indices_ordenados = np.argsort(-scores)[:k]
        return [(self.faqs[i], float(scores[i])) for i in indices_ordenados]


def formatar_saida(resultados, debug=False):
    """Formata a saída no estilo do faq.py original, citando a fonte.

    Sem etapa de geração: a "resposta" é o texto original da FAQ de maior
    score, com citação explícita da fonte (id da FAQ).
    """
    if not resultados:
        return "Não encontrei nada parecido"

    melhor_faq, melhor_score = resultados[0]

    linhas = []
    if melhor_score < LIMIAR_SEM_RESPOSTA:
        linhas.append("Não encontrei nada parecido no meu material.")
        linhas.append(f"(maior similaridade encontrada: {melhor_score:.3f}, abaixo do limiar {LIMIAR_SEM_RESPOSTA})")
    else:
        linhas.append(melhor_faq["resposta"])
        linhas.append(f"Fonte: FAQ #{melhor_faq['id']} — \"{melhor_faq['pergunta']}\"")

    if debug:
        linhas.append("")
        linhas.append(f"--- top-{len(resultados)} (debug) ---")
        for faq, score in resultados:
            linhas.append(f"  FAQ #{faq['id']:2d} | score={score:.3f} | {faq['pergunta']}")

    return "\n".join(linhas)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    argumentos = sys.argv[1:]
    debug = "--debug" in argumentos
    argumentos = [a for a in argumentos if a != "--debug"]
    pergunta = " ".join(argumentos)

    if not pergunta.strip():
        print('Uso: python faq_rag.py "sua pergunta" [--debug]')
        return

    faqs = carregar_faqs(CAMINHO_FAQS)
    if faqs is None:
        return

    indice = IndiceRAG(faqs)
    resultados = indice.buscar(pergunta, k=TOP_K)
    print(formatar_saida(resultados, debug=debug))


def montar_contexto_top_k(resultados):
    """Formata o top-k recuperado como texto de contexto para o LLM."""
    blocos = [f"FAQ #{faq['id']}: {faq['pergunta']}\nResposta: {faq['resposta']}" for faq, _score in resultados]
    return "\n\n".join(blocos)


def gerar_resposta_rag(client, indice, pergunta, k=TOP_K):
    """Pipeline RAG completo: retrieval + geração, para comparação com o CAG.

    Retorna um dicionário com o texto gerado, tokens, latência e também os
    dados de retrieval (top-k e scores), para permitir avaliar acerto de
    retrieval e qualidade da geração separadamente.
    """
    resultados = indice.buscar(pergunta, k=k)
    contexto = montar_contexto_top_k(resultados)
    conteudo_usuario = f"Contexto (FAQs recuperadas):\n{contexto}\n\nPergunta do usuário: {pergunta}"

    # Sem caching: o contexto (top-3 recuperado) muda a cada pergunta, então
    # não há prefixo estável para reaproveitar. A instrução vai como string
    # simples no system.
    saida_geracao = gemini_client.gerar_resposta(client, SYSTEM_INSTRUCTION_GERACAO, conteudo_usuario)
    saida_geracao["top_k_recuperado"] = [
        {"faq_id": faq["id"], "score": round(score, 4)} for faq, score in resultados
    ]
    return saida_geracao


if __name__ == "__main__":
    main()

# NOTA (Checkpoint B, concluído): com o acesso à Anthropic liberado, a geração
# via LLM foi implementada em gerar_resposta_rag() acima — passa o top-k
# recuperado como contexto e pede resposta natural com citação da(s) FAQ(s).
# O modo RAG não usa prompt caching de propósito (o contexto muda a cada
# pergunta); o caching de prefixo real fica só no lado CAG (ver faq_cag.py).
# A função main()/formatar_saida() abaixo permanece como um modo de inspeção
# de retrieval puro (sem LLM), útil para diagnosticar acerto de recuperação.
