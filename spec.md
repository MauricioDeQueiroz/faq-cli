## parte 1 - spec versão anterior

• Resultados esperados — o que o app entrega, em uma frase.
    Um buscador de FAQ (Perguntas Frequentes) por linha de comando, onde recebe uma pergunta em texto e devolve a respota mais relevante.

• Escopo e limites — o que está dentro e, principalmente, o que está fora.
   Dentro: busca por palavra-chave numa base fixa de ~20 FAQs; normalização básica do input (lowercase, remoção de acento/pontuação); retorno da FAQ mais relevante encontrada, ou a mais próxima com mensagem de sugestão quando não houver correspondência clara; execução via terminal, uma consulta por execução.
    Fora: busca semântica/embeddings (fica pra semana 3); correção ortográfica avançada; múltiplos idiomas; interface gráfica; loop contínuo de perguntas na mesma sessão; histórico ou aprendizado de uso.

• Restrições — linguagem, bibliotecas permitidas, tempo, etc.
    Linguagem Python. Dados das FAQs em arquivo JSON local. Priorizar bibliotecas nativas do Python (ex.: json, re); 
    libs externas só se realmente necessário e leves (nada de frameworks pesados). Sem conexão com internet/API externa;
    Tempo total do projeto: ~20h da semana, dividido entre estudo, spec, plano e implementação.

• Decisões já tomadas — escolhas que você não vai rediscutir (ex.: “CLI, não web”).
    CLI, não web. 

• Quebra de tarefas — em fatias verticais pequenas.
    Criar a base de ~20 FAQs em arquivo JSON e carregar no app;
    Receber input do usuário via terminal (execução única);
    Normalizar o texto de entrada (lowercase, remover acento/pontuação);
    Comparar o input normalizado com as FAQs e retornar a mais relevante;
    Implementar tratamento de não-correspondência (comportamento definido no Escopo);
    Escrever conjunto de testes e validar critério de acerto (detalhado em Critérios de verificação);

• Critérios de verificação — como você vai provar que funciona (precisa ser testável).
    Criterios exemplar: 
    Escrever um conjunto de perguntas de teste (mínimo 10), cada uma com a FAQ esperada já conhecida;
    Quando não houver correspondência clara, o app deve exibir mensagem de "Pergunta não encontrado" + sugestão da FAQ mais próxima, sem travar ou lançar erro.
    Normalização deve ser consistente: variações de acento/pontuação no input (ex.: "Como faço Login?" vs "como faco login") devem retornar a mesma FAQ;
    De 10 perguntas de teste, pelo menos 8 (80%) devem retornar a FAQ correta esperada

## parte 2 - As 5 perguntas que o Claude levantou e as minhas respostas

Li a spec inteira. Está bem estruturada, mas há decisões centrais ainda implícitas — principalmente no coração do app (o que é "relevância"). Como PM cético, estas são as 5 perguntas que mais reduziriam a ambiguidade antes de você implementar:

1. Como exatamente se calcula a "FAQ mais relevante"?

Este é o buraco central da spec. "Busca por palavra-chave" e "mais relevante" não definem o algoritmo. Você compara por:
- contagem de palavras em comum entre input e pergunta da FAQ?
- proporção (palavras em comum ÷ total)?
- peso por palavra rara vs. comum?

Sem isso definido, "mais relevante" é subjetivo e você não consegue justi da Y. Sugiro fixar uma regra simples e explícita (ex.: score = nº depalavras significativas em comum, desempate pela maior proporção).

2. O que separa "correspondência clara" de "não encontrado"?

A spec diz que abaixo de um certo ponto vira "Pergunta não encontrada" + sugestão. Mas qual é o limiar numérico? Ex.: "pelo menos 1 palavra em comum" ou "score ≥ 2" ou
"proporção ≥ 30%". Isso é o que torna o critério de verificação testável e de um número que não existe.

3. Contra o quê o input é comparado — pergunta, resposta ou keywords?

Cada FAQ tem pergunta + resposta. O match roda contra:
- só o texto da pergunta da FAQ?
- pergunta + lista de palavras-chave curadas que você adiciona em cada FA

A segunda opção melhora muito o acerto (paráfrases), mas muda a estrutura antes de criar as 20 FAQs, senão você recria a base depois.

4. Como o usuário passa a pergunta e o que exatamente aparece na tela?

"Execução única via terminal" ainda deixa aberto:
- Entrada: argumento na linha de comando (python faq.py "como faço login") ou input() que pergunta interativamente uma vez?
- Saída: só a resposta? pergunta + resposta? mostra o score/quão confiant

Isso define seu contrato de I/O e os testes dependem dele.

5. As 10 perguntas de teste são "fáceis" ou paráfrases realistas?

O critério de 80% só tem valor se as perguntas de teste não forem cópias s do JSON — senão 100% é trivial e não prova nada. Você se compromete aincluir paráfrases (ex.: "esqueci minha senha" para uma FAQ "como recuperar senha")? E no caso de "não encontrado": o teste valida que a sugestão certa apareceu, ou basta não travar?

Respostas às perguntas do PM cético:

1. Cálculo de relevância: score = (nº de palavras do input, após normalização e 
   remoção de stopwords, que também aparecem no texto da "pergunta" da FAQ) ÷ 
   (nº total de palavras do input, normalizadas).

2. Limiar de "não encontrado": score < 30%.

3. Comparação: só contra o texto da "pergunta" da FAQ (sem campo de tags/keywords).

4. Entrada/saída: entrada via argumento de linha de comando 
   (python faq.py "pergunta"). Saída: pergunta encontrada + resposta juntas.

5. Perguntas de teste: paráfrases reais (não repetição do texto oficial). 
   Meta de acerto ajustada para 70% (7 de 10), reconhecendo o limite de 
   matching lexical puro contra paráfrases distantes.

   - spec nova

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
- De 10 perguntas de teste, pelo menos 7 (70%) devem retornar a FAQ correta esperada.