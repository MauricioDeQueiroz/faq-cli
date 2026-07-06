"""Testes da Fase 4 — limiar de decisão e saída formatada (três faixas).

Rodar da raiz do projeto:
    python -m unittest tests.test_saida -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faq import LIMIAR, formatar_saida  # noqa: E402


class TestFormatarSaida(unittest.TestCase):
    def setUp(self):
        self.faq = {"pergunta": "Como recuperar minha senha?", "resposta": "Clique em 'Esqueci a senha'."}

    def test_match_direto_pergunta_e_resposta(self):
        # score >= LIMIAR -> pergunta oficial + resposta, sem prefixo.
        saida = formatar_saida(self.faq, 0.75)
        self.assertEqual(saida, f"{self.faq['pergunta']}\n{self.faq['resposta']}")
        self.assertNotIn("Sugestao de resposta", saida)

    def test_match_direto_no_limiar_exato(self):
        # Borda: score == LIMIAR conta como match direto (>=).
        saida = formatar_saida(self.faq, LIMIAR)
        self.assertEqual(saida, f"{self.faq['pergunta']}\n{self.faq['resposta']}")

    def test_sugestao_com_prefixo(self):
        # 0 < score < LIMIAR -> mesma FAQ, mesmo formato, prefixada.
        saida = formatar_saida(self.faq, 0.20)
        self.assertEqual(
            saida,
            f"Sugestao de resposta: {self.faq['pergunta']}\n{self.faq['resposta']}",
        )
        self.assertIn(self.faq["resposta"], saida)

    def test_nada_parecido_com_score_zero(self):
        # score == 0 -> mensagem fixa, sem sugerir nenhuma FAQ.
        saida = formatar_saida(self.faq, 0.0)
        self.assertEqual(saida, "Não encontrei nada parecido")

    def test_nada_parecido_ignora_faq_none(self):
        # score 0 com faq None (lista vazia de FAQs) nao deve lancar excecao.
        saida = formatar_saida(None, 0.0)
        self.assertEqual(saida, "Não encontrei nada parecido")


if __name__ == "__main__":
    unittest.main()
