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
    Quando não houver correspondência clara, o app deve exibir mensagem de "Pergunta não encontrado" + sugestão da FAQ mais próxima, sem travar ou lançar erro. Se a correspondência for menor que 30%, exibe apenas "Pergunta não encontrada";
    Normalização deve ser consistente: variações de acento/pontuação no input (ex.: "Como faço Login?" vs "como faco login") devem retornar a mesma FAQ;
    De 10 perguntas de teste, pelo menos 8 (80%) devem retornar a FAQ correta esperada