"""Testes da Fase 5 — validacao do criterio de acerto (end-to-end).

Mede a taxa de acerto sobre pacarafrases reais (tests/test_cases.json) e
valida os caminhos de nao-correspondencia e de consistencia de normalizacao.

Regra da spec: o algoritmo de score e FIXO. Se a taxa cair, o ajuste seria em
stopwords/base de FAQs — nunca no calculo de score.

Rodar da raiz do projeto:
    python -m unittest tests.test_faq -v
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faq import (  # noqa: E402
    CAMINHO_FAQS,
    LIMIAR,
    carregar_faqs,
    formatar_saida,
    melhor_faq,
    normalizar,
)

CAMINHO_CASOS = Path(__file__).resolve().parent / "test_cases.json"

# Meta oficial da especificacao: >= 80% (8/10). Entregamos exatamente 80%,
# entao este piso trava na fronteira: qualquer regressao num caso derruba o teste.
TAXA_MINIMA = 0.80


def id_respondido(texto, faqs):
    """Devolve o id (1-indexado) da FAQ que o sistema retornaria, ou None.

    None = caminho "nada parecido" (score 0 em todas as FAQs), espelhando a
    faixa da Fase 4. Sugestao (0 < score < LIMIAR) ainda aponta uma FAQ.
    """
    faq, score = melhor_faq(normalizar(texto), faqs)
    if score == 0 or faq is None:
        return None
    return faqs.index(faq) + 1


class TestTaxaDeAcerto(unittest.TestCase):
    def setUp(self):
        self.faqs = carregar_faqs(CAMINHO_FAQS)
        self.assertIsNotNone(self.faqs, "base de FAQs deve carregar")
        with open(CAMINHO_CASOS, encoding="utf-8") as f:
            self.casos = json.load(f)

    def test_pelo_menos_dez_casos(self):
        # O plano pede >= 10 perguntas de teste.
        self.assertGreaterEqual(len(self.casos), 10)

    def test_taxa_de_acerto_atinge_meta(self):
        acertos = 0
        falhas = []
        for caso in self.casos:
            obtido = id_respondido(caso["input"], self.faqs)
            if obtido == caso["esperado_id"]:
                acertos += 1
            else:
                falhas.append(f"  {caso['input']!r}: esperado {caso['esperado_id']}, obtido {obtido}")
        taxa = acertos / len(self.casos)
        msg = (
            f"\nTaxa de acerto: {acertos}/{len(self.casos)} = {taxa:.0%} "
            f"(meta >= {TAXA_MINIMA:.0%})\nFalhas conhecidas:\n" + "\n".join(falhas)
        )
        self.assertGreaterEqual(taxa, TAXA_MINIMA, msg)


class TestCaminhoNaoCorrespondencia(unittest.TestCase):
    def setUp(self):
        self.faqs = carregar_faqs(CAMINHO_FAQS)

    def test_pergunta_fora_do_escopo_nao_quebra(self):
        # "quero comprar uma bicicleta" nao tem intersecao com nenhuma FAQ.
        faq, score = melhor_faq(normalizar("quero comprar uma bicicleta"), self.faqs)
        self.assertEqual(score, 0.0)
        self.assertEqual(formatar_saida(faq, score), "Não encontrei nada parecido")


class TestConsistenciaNormalizacao(unittest.TestCase):
    def setUp(self):
        self.faqs = carregar_faqs(CAMINHO_FAQS)

    def test_variacoes_de_acento_e_pontuacao_mesma_faq(self):
        # Mesma pergunta com acento/caixa/pontuacao diferentes -> mesma FAQ.
        variantes = ["Como faço login?", "COMO FACO LOGIN!!!", "como faco login"]
        ids = {id_respondido(v, self.faqs) for v in variantes}
        self.assertEqual(len(ids), 1, f"variantes divergiram: {ids}")
        # e o LIMIAR continua sendo o mesmo objeto usado na decisao (sanidade)
        self.assertGreater(LIMIAR, 0)


if __name__ == "__main__":
    unittest.main()
