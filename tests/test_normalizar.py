"""Testes da Fase 2 — normalização de texto.

Rodar da raiz do projeto:
    python -m unittest tests.test_normalizar -v
"""

import sys
import unittest
from pathlib import Path

# Permite importar faq.py estando na raiz do projeto (pasta pai de tests/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faq import normalizar  # noqa: E402


class TestNormalizar(unittest.TestCase):
    def test_criterio_principal_acento_e_maiuscula(self):
        # Critério "Pronto quando" do plano: as duas formas viram a mesma lista.
        a = normalizar("Como faço Login?")
        b = normalizar("como faco login")
        self.assertEqual(a, b)
        self.assertEqual(a, ["login"])  # "como" e "faco" são stopwords

    def test_consistencia_acento_e_pontuacao(self):
        # Variações de caixa, espaços e pontuação devem colapsar no mesmo token.
        casos = [
            "Pagamento, recusado!!!",
            "pagamento recusado",
            "PAGAMENTO   RECUSADO...",
        ]
        resultados = [normalizar(c) for c in casos]
        for r in resultados:
            self.assertEqual(r, resultados[0])
        self.assertEqual(resultados[0], ["pagamento", "recusado"])

    def test_stopword_acentuada_e_tratada(self):
        # "faço" (com acento) normaliza para "faco", que está na lista de stopwords.
        self.assertEqual(normalizar("faço"), [])

    def test_remove_pontuacao(self):
        self.assertEqual(normalizar("senha!!!"), ["senha"])
        self.assertEqual(normalizar("e-mail"), ["mail"])  # "e" é stopword; sobra "mail"

    def test_texto_so_de_stopwords_vira_lista_vazia(self):
        self.assertEqual(normalizar("como que eu faço para"), [])

    def test_string_vazia(self):
        self.assertEqual(normalizar(""), [])

    def test_numeros_sao_mantidos(self):
        self.assertEqual(normalizar("boleto 123"), ["boleto", "123"])


if __name__ == "__main__":
    unittest.main()
