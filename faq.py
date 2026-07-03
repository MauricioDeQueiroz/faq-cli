"""FAQ CLI — Fase 0 (esqueleto e contrato).

Uso: python faq.py "sua pergunta"

Nesta fase o programa apenas ecoa de volta a pergunta recebida, para validar
o fluxo de ponta a ponta no terminal (inclusive acentuação no Windows/PowerShell).
"""

import sys


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

    # Stub: ecoa o input (com acento) só para validar o fluxo do terminal.
    print(f'Você perguntou: {pergunta}')


if __name__ == "__main__":
    main()
