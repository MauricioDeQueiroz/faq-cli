"""FAQ CLI — Fase 4 (limiar de decisão e saída formatada).

Uso: python faq.py "sua pergunta"

Nesta fase o programa normaliza a pergunta, calcula um score de relevância
contra cada FAQ, escolhe a de maior score e aplica o limiar de 30% em três
faixas: match direto, sugestão (com prefixo) e "nada parecido".
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

# Caminho do JSON relativo ao próprio script (funciona independente do diretório
# de onde o programa é chamado).
CAMINHO_FAQS = Path(__file__).resolve().parent / "data" / "faqs.json"

# Limiar de decisão: score >= 30% conta como match direto; abaixo disso (mas > 0)
# vira sugestão; score 0 em todas as FAQs vira "nada parecido".
LIMIAR = 0.30

# Stopwords PT-BR curtas e fixas. IMPORTANTE: guardadas já na forma NORMALIZADA
# (minúsculas e SEM acento), pois o filtro é aplicado depois de remover acentos.
# Ex.: "faço" vira "faco" na normalização, então listamos "faco", não "faço".
STOPWORDS = frozenset({
    "a", "o", "as", "os", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "no", "na", "nos", "nas",
    "em", "e", "ou", "que", "se", "com", "sem", "por", "para",
    "eu", "tu", "voce", "me", "te", "lhe",
    "meu", "minha", "meus", "minhas", "sua", "seu",
    "como", "faco", "fazer", "quero", "qual", "quais", "onde",
})


def carregar_faqs(caminho):
    """Abre o JSON de FAQs (UTF-8) e devolve a lista de {pergunta, resposta}.

    Em caso de arquivo ausente ou JSON inválido, devolve None (o chamador
    trata com mensagem amigável, sem stacktrace).
    """
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Erro: base de FAQs não encontrada em {caminho}.")
        return None
    except json.JSONDecodeError as e:
        print(f"Erro: base de FAQs está com JSON inválido ({e}).")
        return None


def normalizar(texto):
    """Converte um texto livre numa lista de tokens comparáveis.

    Passos: (1) minúsculas, (2) remove acentos, (3) remove pontuação
    (mantém só letras/números/espaço), (4) tokeniza, (5) tira stopwords.
    Assim "Como faço Login?" e "como faco login" viram a mesma lista.
    """
    # 1. minúsculas
    texto = texto.lower()
    # 2. remove acentos: decompõe (NFKD) e descarta os caracteres combinantes
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    # 3. remove pontuação: mantém apenas letras, números e espaço
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    # 4. tokeniza
    tokens = texto.split()
    # 5. remove stopwords (a lista já está na forma sem acento)
    return [t for t in tokens if t not in STOPWORDS]


def calcular_score(tokens_input, tokens_faq):
    """Fração dos tokens (únicos) da pergunta que aparecem na FAQ.

    Usa `set` nos DOIS lados, então repetição no input não distorce o score:
    "senha senha login" com tudo batendo dá 1.0, não 0.66. Formalmente:
        score = |set(input) ∩ set(faq)| / |set(input)|
    Borda: input vazio após normalização → 0.0 (sem divisão por zero).
    """
    conjunto_input = set(tokens_input)
    if not conjunto_input:
        return 0.0
    intersecao = conjunto_input & set(tokens_faq)
    return len(intersecao) / len(conjunto_input)


def melhor_faq(tokens_input, faqs):
    """Retorna (faq, score) da FAQ de maior score de relevância.

    Desempate: vence a PRIMEIRA FAQ na ordem do arquivo. Para isso, só
    substituímos o melhor quando o score é ESTRITAMENTE maior (`>`), nunca
    em empate. Retorna (None, 0.0) se a lista de FAQs estiver vazia.
    """
    melhor = None
    melhor_score = -1.0
    for faq in faqs:
        tokens_faq = normalizar(faq["pergunta"])
        score = calcular_score(tokens_input, tokens_faq)
        if score > melhor_score:
            melhor_score = score
            melhor = faq
    if melhor is None:
        return None, 0.0
    return melhor, melhor_score


def formatar_saida(faq, score):
    """Monta o texto de saída aplicando o limiar de 30% em três faixas.

    - score >= LIMIAR (match direto): pergunta oficial + resposta.
    - 0 < score < LIMIAR (sugestão): a mesma FAQ, no mesmo formato, prefixada
      com "Sugestao de resposta: ".
    - score == 0 (nada parecido): "Não encontrei nada parecido", sem sugerir
      nada (evita sugerir a FAQ #1 por desempate com todos os scores zerados).
    """
    if score == 0:
        return "Não encontrei nada parecido"
    if score >= LIMIAR:
        return f"{faq['pergunta']}\n{faq['resposta']}"
    return f"Sugestao de resposta: {faq['pergunta']}\n{faq['resposta']}"


def main():
    # Encoding do stdout (Windows/PowerShell): força UTF-8 para não estourar
    # UnicodeEncodeError ao imprimir acentos. Alternativa documentada:
    # definir a variável de ambiente PYTHONIOENCODING=utf-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Python >= 3.7
    except AttributeError:
        pass

    # Lê a pergunta como a frase inteira — funciona com ou sem aspas.
    pergunta = " ".join(sys.argv[1:])

    # Ausência de argumento: mensagem de uso clara e sai.
    if not pergunta.strip():
        print('Uso: python faq.py "sua pergunta"')
        return

    # Carrega a base de FAQs.
    faqs = carregar_faqs(CAMINHO_FAQS)
    if faqs is None:
        return

    # Normaliza a pergunta e escolhe a FAQ de maior score.
    tokens = normalizar(pergunta)
    faq, score = melhor_faq(tokens, faqs)

    # Aplica o limiar de decisão e imprime a saída formatada.
    print(formatar_saida(faq, score))


if __name__ == "__main__":
    main()
