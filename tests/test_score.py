"""Testes da Fase 3 — score de relevância e escolha da melhor FAQ.

Rodar da raiz do projeto:
    python -m unittest tests.test_score -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faq import CAMINHO_FAQS, calcular_score, carregar_faqs, melhor_faq, normalizar  # noqa: E402


class TestCalcularScore(unittest.TestCase):
    def test_todos_os_tokens_batem(self):
        self.assertEqual(calcular_score(["login", "senha"], ["login", "senha"]), 1.0)

    def test_metade_bate(self):
        self.assertEqual(calcular_score(["login", "senha"], ["login", "pedido"]), 0.5)

    def test_repeticao_no_input_nao_distorce(self):
        # "senha senha login" com tudo batendo deve dar 1.0, nao 0.66 (set dos dois lados).
        self.assertEqual(calcular_score(["senha", "senha", "login"], ["senha", "login"]), 1.0)

    def test_input_vazio_da_zero_sem_erro(self):
        # Borda: input vazio (tudo era stopword) -> 0.0, sem divisao por zero.
        self.assertEqual(calcular_score([], ["login"]), 0.0)

    def test_nenhum_token_bate(self):
        self.assertEqual(calcular_score(["boleto"], ["login", "senha"]), 0.0)


class TestMelhorFaq(unittest.TestCase):
    def setUp(self):
        self.faqs = carregar_faqs(CAMINHO_FAQS)
        self.assertIsNotNone(self.faqs, "base de FAQs deve carregar")

    def test_pergunta_obvia_retorna_faq_correta(self):
        # Criterio "Pronto quando": pergunta obvia -> FAQ certa com score coerente.
        faq, score = melhor_faq(normalizar("esqueci minha senha, como recuperar"), self.faqs)
        self.assertIn("senha", faq["pergunta"].lower())
        self.assertGreater(score, 0.0)

    def test_pergunta_sobre_pix(self):
        faq, score = melhor_faq(normalizar("quero pagar com pix"), self.faqs)
        self.assertIn("pix", faq["pergunta"].lower())
        self.assertGreater(score, 0.0)

    def test_desempate_vence_primeira_do_arquivo(self):
        # Duas FAQs com exatamente o mesmo token relevante -> vence a primeira da lista.
        faqs = [
            {"pergunta": "login primeiro", "resposta": "A"},
            {"pergunta": "login segundo", "resposta": "B"},
        ]
        faq, score = melhor_faq(["login"], faqs)
        self.assertEqual(faq["resposta"], "A")
        self.assertEqual(score, 1.0)

    def test_lista_vazia_de_faqs(self):
        faq, score = melhor_faq(["login"], [])
        self.assertIsNone(faq)
        self.assertEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()
