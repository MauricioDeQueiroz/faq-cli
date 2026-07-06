## Spec nova — FAQ CLI

**Resultados esperados**
Um buscador de FAQ (Perguntas Frequentes) por linha de comando, onde recebe uma pergunta em texto e devolve a resposta mais relevante.

**Escopo e limites**
Dentro: busca por palavra-chave numa base fixa de ~20 FAQs; normalização básica do input (lowercase, remoção de acento/pontuação, remoção de stopwords); retorno da FAQ mais relevante encontrada, ou a mais próxima com mensagem de sugestão quando não houver correspondência clara; execução via terminal, uma consulta por execução.
Fora: busca semântica/embeddings (fica pra semana 3); correção ortográfica avançada; múltiplos idiomas; interface gráfica; loop contínuo de perguntas na mesma sessão; histórico ou aprendizado de uso.

**Restrições**
Linguagem Python. Dados das FAQs em arquivo JSON local. Priorizar bibliotecas nativas do Python (ex.: json, re). Libs externas só se realmente necessário e leves (nada de frameworks pesados). Sem conexão com internet/API externa. Tempo total do projeto: ~20h da semana, dividido entre estudo, spec, plano e implementação.

**Decisões já tomadas**
- CLI, não web.
- Matching lexical por contagem de palavras em comum (sem embeddings).
- Input via argumento de linha de comando (não interativo).
- Comparação só contra o texto da "pergunta" da FAQ (sem campo de tags/keywords).

**Cálculo de relevância**
Score = (nº de palavras do input, após normalização e remoção de stopwords, que também aparecem no texto da "pergunta" da FAQ) ÷ (nº total de palavras do input, normalizadas).

**Limiar de decisão**
Score < 30% → "Pergunta não encontrada" + sugestão da FAQ mais próxima.
Score ≥ 30% → retorna a FAQ mais relevante.

**Contrato de entrada e saída**
Entrada: argumento de linha de comando. Exemplo: `python faq.py "como faço login"`.
Saída: pergunta encontrada + resposta, juntas.

**Quebra de tarefas — fatias verticais pequenas**
1. Criar a base de ~20 FAQs em arquivo JSON e carregar no app.
2. Receber input do usuário via argumento de linha de comando (execução única).
3. Normalizar o texto de entrada (lowercase, remover acento/pontuação, remover stopwords).
4. Comparar o input normalizado com as FAQs (contagem de palavras em comum) e retornar a mais relevante.
5. Implementar tratamento de não-correspondência (score < 30% → mensagem + sugestão).
6. Escrever conjunto de testes (paráfrases reais) e validar critério de acerto.

**Critérios de verificação**
- Escrever um conjunto de perguntas de teste (mínimo 10, paráfrases reais, não repetição do texto oficial), cada uma com a FAQ esperada já conhecida.
- Quando o score for menor que 30%, o app deve exibir mensagem de "Pergunta não encontrada" + sugestão da FAQ mais próxima, sem travar ou lançar erro.
- Normalização deve ser consistente: variações de acento/pontuação no input (ex.: "Como faço Login?" vs "como faco login") devem retornar a mesma FAQ.
- De 10 perguntas de teste, pelo menos 8 (80%) devem retornar a FAQ correta esperada.