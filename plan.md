# Plano técnico — FAQ CLI

Plano de implementação em fases derivado de [spec.md](spec.md). Cada fase é uma fatia vertical
pequena, testável isoladamente. Nenhuma fase depende de código ainda não escrito nas fases posteriores.

## Princípios de arquitetura

- **Só biblioteca nativa**: `json`, `re`, `sys`, `unicodedata`. Sem libs externas.
- **Separação de responsabilidades** em funções puras (fáceis de testar sem tocar no terminal):
  - carregar dados (I/O)
  - normalizar texto (puro)
  - calcular score (puro)
  - escolher a melhor FAQ (puro)
  - formatar/imprimir saída (I/O)
- **Entrada única por execução**: sem loop, sem estado entre chamadas.
- **Módulo importável sem efeito colateral**: toda a orquestração fica atrás de uma função
  `main()` chamada apenas sob `if __name__ == "__main__"`. Assim os testes podem `import faq`
  sem disparar o CLI (nem estourar em `sys.argv` inexistente).

## Estrutura de arquivos prevista

```
faq-cli/
├── faq.py            # ponto de entrada (CLI) + orquestração
├── data/
│   └── faqs.json     # base de ~20 FAQs
├── tests/
│   └── test_faq.py   # perguntas de teste (paráfrases) + testes de normalização
├── spec.md
└── plan.md
```

---

## Fase 0 — Esqueleto e contrato

**Objetivo:** ter `python faq.py "texto"` rodando de ponta a ponta, mesmo que devolvendo algo fixo.

- Criar `faq.py` com toda a lógica dentro de `main()`, executada só sob `if __name__ == "__main__"`.
- Ler a pergunta como `" ".join(sys.argv[1:])` — funciona **com ou sem aspas** (ex.: `python faq.py como faço login` pega a frase inteira, não só a primeira palavra).
- Tratar ausência de argumento (`sys.argv[1:]` vazio): mensagem de uso clara (`Uso: python faq.py "sua pergunta"`) e sair.
- **Encoding do stdout (Windows/PowerShell):** logo no início do `main()`, forçar UTF-8 para não estourar `UnicodeEncodeError` ao imprimir acentos (`ç`, `ã`, `á`). Usar `sys.stdout.reconfigure(encoding="utf-8")` (Python ≥3.7), com `PYTHONIOENCODING=utf-8` como alternativa documentada. Isso é pré-requisito do critério "sem travar ou lançar erro".
- Imprimir de volta o input (stub) — incluindo um texto acentuado — só para validar o fluxo do terminal no Windows/PowerShell.

**Pronto quando:** `python faq.py "teste"` roda sem erro, `python faq.py teste sem aspas` também captura a frase toda, `python faq.py` (sem argumento) mostra ajuda, e imprimir acento não trava.

---

## Fase 1 — Base de FAQs (JSON) e carregamento

Corresponde à fatia 1 da spec.

- Definir o formato do JSON: lista de objetos `{ "pergunta": "...", "resposta": "..." }`.
- Popular `data/faqs.json` com ~20 FAQs realistas (ex.: login, senha, cadastro, pagamento, etc.).
- Função `carregar_faqs(caminho)` que abre o arquivo com `encoding="utf-8"` e retorna a lista.
- Tratar erro de arquivo ausente / JSON inválido com mensagem amigável (sem stacktrace).

**Decisão a confirmar:** caminho do JSON relativo ao script (usar `pathlib`/`__file__` para
funcionar independente do diretório de onde se chama).

**Pronto quando:** o app carrega as 20 FAQs e consegue listar quantas foram lidas.

---

## Fase 2 — Normalização de texto

Corresponde à fatia 3 da spec. É o núcleo que garante o critério de "acento/pontuação consistentes".

- Função `normalizar(texto) -> list[str]`:
  1. lowercase
  2. remover acentos (`unicodedata.normalize('NFKD', ...)` + filtrar combinantes)
  3. remover pontuação (`re`, manter só letras/números/espaço)
  4. dividir em tokens
  5. remover stopwords (lista PT-BR curta e fixa: "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "como", "faço", "por"…)
- Manter a lista de stopwords como constante no topo do módulo, fácil de ajustar.

**Decisão (adiada de propósito):** a stopword-list fica **como está por enquanto**. Ela é agressiva
e, em perguntas curtas, pode deixar só 1 token (ex.: "como faço login" → `["login"]`), tornando o
score binário (0% ou 100%). **Não ajustar preventivamente** — primeiro medir a taxa de acerto na
Fase 5; só reduzir a lista se ficarmos abaixo de 70%.

**Cuidado:** "faço" vira "faco" após remover acento — a stopword-list precisa considerar a forma
**já normalizada** (sem acento), senão o filtro não pega.

**Pronto quando:** `normalizar("Como faço Login?")` e `normalizar("como faco login")` produzem a
mesma lista de tokens.

---

## Fase 3 — Score de relevância e escolha da melhor FAQ

Corresponde à fatia 4 da spec.

- Pré-normalizar o texto da "pergunta" de cada FAQ (uma vez, no carregamento ou no cálculo).
- Função `calcular_score(tokens_input, tokens_faq) -> float`:
  - **`set` nos dois lados** (numerador *e* denominador), não contagem bruta. Formalmente:
    `score = |set(input) ∩ set(faq)| ÷ |set(input)|`.
  - Isso garante que repetição no input não distorça o score: "senha senha login" com tudo batendo
    dá **100%**, não 66%. Palavra conta uma vez de ambos os lados.
  - **Caso de borda:** input vazio após normalização (`set(input)` vazio → tudo era stopword) → score 0, sem divisão por zero.
- Função `melhor_faq(tokens_input, faqs) -> (faq, score)`: retorna a de maior score.
- **Desempate (decidido):** em caso de empate no score, vence a **primeira FAQ na ordem do arquivo JSON**. Implementação: iterar preservando a ordem e substituir o melhor só quando o score for **estritamente maior** (`>`), nunca em empate (`>=`).

**Pronto quando:** dada uma pergunta óbvia, retorna a FAQ correta com score coerente.

---

## Fase 4 — Limiar de decisão e saída

Corresponde às fatias 2 e 5 da spec.

- Aplicar o limiar de 30% em **três faixas** (a de maior score sempre define a decisão):
  - **`score >= 0.30` (match direto)** → imprimir **pergunta oficial + resposta** juntas.
  - **`0 < score < 0.30` (sugestão)** → imprimir a **mesma FAQ de maior score**, no **mesmo formato do match direto** (pergunta oficial + resposta), apenas prefixado com **`Sugestao de resposta: ...`**. É a "FAQ mais próxima" da spec, sinalizada como palpite.
  - **`score == 0` em todas as FAQs (nada parecido)** → imprimir **"Não encontrei nada parecido"** e **não** sugerir nada. Evita sugerir a FAQ #1 por acaso (que seria a vencedora do desempate com todos os scores zerados).
- Nunca lançar exceção para o usuário: entrada vazia, sem match, etc. sempre resultam em mensagem tratada.
- Função `formatar_saida(...)` separada da lógica, para poder testar o texto (as três faixas).

**Pronto quando:** as três faixas produzem a saída certa — match direto, sugestão com prefixo, e "nada parecido" — sem travar.

---

## Fase 5 — Testes e validação do critério de acerto

Corresponde à fatia 6 e aos critérios de verificação da spec.

- `tests/test_faq.py` com:
  - **≥10 perguntas de teste** (paráfrases reais, não cópia do texto oficial), cada uma com a FAQ esperada.
  - Teste de **consistência de normalização** (variações de acento/pontuação → mesma FAQ).
  - Teste do **caminho de não-correspondência** (score < 30% → mensagem certa, sem erro).
- Rodar e medir: **≥7 de 10 (70%) corretas**. Se abaixo, iterar em stopwords/base de FAQs (não mudar o algoritmo de score, que é decisão fechada na spec).
- Usar `unittest` nativo (sem pytest) para respeitar a restrição de libs.

**Pronto quando:** a suíte roda com `python -m unittest` e atinge ≥70% de acerto.

---

## Ordem de execução e pontos de decisão

| Fase | Entrega | Decisão pendente |
|------|---------|------------------|
| 0 | CLI roda ponta a ponta | — |
| 1 | JSON + carregamento | caminho relativo do JSON |
| 2 | Normalização | — (stopword-list mantida; revisar só se acerto < 70% na Fase 5) |
| 3 | Score + melhor FAQ | — (desempate = primeira do JSON; `set` nos dois lados) |
| 4 | Limiar + saída | — (3 faixas: match / sugestão com prefixo / nada parecido) |
| 5 | Testes | conteúdo das 10 paráfrases |

## Riscos / atenção

- **Stopwords vs. acento:** normalizar antes de comparar com a lista (ver Fase 2).
- **Divisão por zero:** input só com stopwords → `set(input)` vazio → score 0 (ver Fase 3).
- **Encoding no Windows:** `encoding="utf-8"` ao abrir o JSON **e** `sys.stdout.reconfigure(encoding="utf-8")` na saída, senão imprimir acento pode travar (ver Fase 0).
- **Import sem efeito colateral:** CLI só sob `if __name__ == "__main__"`, senão os testes disparam o app ao importar (ver Fase 0).
- **Sugestão arbitrária:** score 0 em todas as FAQs → "Não encontrei nada parecido", nunca sugerir a FAQ #1 por desempate (ver Fase 4).
- **Score binário em queries curtas:** stopword-list agressiva pode deixar 1 token e tornar o score 0%/100%. Decisão: só mexer se a Fase 5 ficar < 70% (ver Fase 2).
- **Taxa de acerto:** se ficar abaixo de 70%, o ajuste é na base de FAQs e nas stopwords — o cálculo de score é fixo por decisão da spec.
