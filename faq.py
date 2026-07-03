"""FAQ CLI — Fase 1 (base de FAQs em JSON e carregamento).

Uso: python faq.py "sua pergunta"

Nesta fase o programa carrega a base de FAQs a partir de data/faqs.json e
informa quantas foram lidas. A busca/resposta em si vem nas próximas fases.
"""

import json
import sys
from pathlib import Path

# Caminho do JSON relativo ao próprio script (funciona independente do diretório
# de onde o programa é chamado).
CAMINHO_FAQS = Path(__file__).resolve().parent / "data" / "faqs.json"


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

    # Stub da Fase 1: confirma o carregamento e ecoa o input.
    print(f"Base carregada: {len(faqs)} FAQs lidas.")
    print(f"Você perguntou: {pergunta}")


if __name__ == "__main__":
    main()
